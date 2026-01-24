#!/usr/bin/env python3
"""
Workflow Status Monitor - Comprehensive monitoring and reporting for CI/CD workflows.

This script provides functionality for:
- Monitoring workflow execution status and health
- Tracking workflow dependencies and sequencing
- Generating workflow status reports
- Detecting workflow anomalies and issues
- Coordinating workflow orchestration

Requirements: All requirements integration
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class WorkflowStatusMonitor:
    """Monitors and reports on CI/CD workflow status and health."""

    def __init__(self, repository: str):
        self.repository = repository
        self.gh_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if not self.gh_token:
            raise ValueError(
                "GitHub token not found. Set GITHUB_TOKEN or GH_TOKEN environment variable."
            )

        # Define workflow dependency graph
        self.workflow_graph = {
            "ci": {
                "file": "ci.yml",
                "depends_on": [],
                "triggers": ["integration-test"],
                "type": "critical",
                "max_duration_minutes": 15,
            },
            "integration-test": {
                "file": "integration-test.yml",
                "depends_on": ["ci"],
                "triggers": ["deploy"],
                "type": "critical",
                "max_duration_minutes": 20,
            },
            "deploy": {
                "file": "deploy.yml",
                "depends_on": ["integration-test"],
                "triggers": ["health-monitor"],
                "type": "critical",
                "max_duration_minutes": 30,
            },
            "health-monitor": {
                "file": "health-monitor.yml",
                "depends_on": [],
                "triggers": ["recovery"],
                "type": "monitoring",
                "max_duration_minutes": 10,
            },
            "recovery": {
                "file": "recovery.yml",
                "depends_on": ["health-monitor"],
                "triggers": ["deploy"],
                "type": "recovery",
                "max_duration_minutes": 15,
            },
            "manual-rollback": {
                "file": "manual-rollback.yml",
                "depends_on": [],
                "triggers": [],
                "type": "manual",
                "max_duration_minutes": 25,
            },
            "workflow-orchestrator": {
                "file": "workflow-orchestrator.yml",
                "depends_on": [],
                "triggers": [],
                "type": "orchestration",
                "max_duration_minutes": 10,
            },
        }

        self.status_cache = {}
        self.last_cache_update = None

    def _run_gh_command(self, command: List[str]) -> Tuple[bool, str]:
        """Run a GitHub CLI command and return success status and output"""
        try:
            env = os.environ.copy()
            env["GH_TOKEN"] = self.gh_token

            result = subprocess.run(
                ["gh"] + command, capture_output=True, text=True, env=env, timeout=60
            )

            return result.returncode == 0, (
                result.stdout.strip()
                if result.returncode == 0
                else result.stderr.strip()
            )
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def get_workflow_runs(self, workflow: str, limit: int = 20) -> List[Dict]:
        """Get recent workflow runs for a specific workflow"""
        workflow_file = self.workflow_graph.get(workflow, {}).get(
            "file", f"{workflow}.yml"
        )

        success, output = self._run_gh_command(
            [
                "run",
                "list",
                "--workflow",
                workflow_file,
                "--limit",
                str(limit),
                "--json",
                "databaseId,status,conclusion,createdAt,updatedAt,headSha,event,displayTitle",
            ]
        )

        if success:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return []
        return []

    def get_workflow_status(self, workflow: str) -> Dict[str, Any]:
        """Get comprehensive status for a specific workflow"""
        runs = self.get_workflow_runs(workflow, 10)

        if not runs:
            return {
                "workflow": workflow,
                "status": "no_runs",
                "health": "unknown",
                "last_run": None,
                "recent_runs": [],
                "issues": ["No recent runs found"],
                "metrics": {},
            }

        latest_run = runs[0]

        # Calculate health based on recent runs
        health_score = self._calculate_workflow_health(runs)

        # Detect issues
        issues = self._detect_workflow_issues(workflow, runs)

        # Calculate metrics
        metrics = self._calculate_workflow_metrics(workflow, runs)

        return {
            "workflow": workflow,
            "status": latest_run.get("status", "unknown"),
            "conclusion": latest_run.get("conclusion"),
            "health": health_score,
            "last_run": latest_run,
            "recent_runs": runs,
            "issues": issues,
            "metrics": metrics,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def _calculate_workflow_health(self, runs: List[Dict]) -> str:
        """Calculate workflow health based on recent runs"""
        if not runs:
            return "unknown"

        # Look at last 5 runs for health assessment
        recent_runs = runs[:5]
        conclusions = [
            run.get("conclusion") for run in recent_runs if run.get("conclusion")
        ]

        if not conclusions:
            return "unknown"

        success_rate = conclusions.count("success") / len(conclusions)

        if success_rate >= 0.8:
            return "healthy"
        elif success_rate >= 0.4:
            return "degraded"
        else:
            return "unhealthy"

    def _detect_workflow_issues(self, workflow: str, runs: List[Dict]) -> List[str]:
        """Detect issues with workflow execution"""
        issues = []

        if not runs:
            issues.append("No recent runs")
            return issues

        latest_run = runs[0]
        workflow_config = self.workflow_graph.get(workflow, {})

        # Check for stuck runs
        if latest_run.get("status") == "in_progress":
            created_at = latest_run.get("createdAt")
            if created_at:
                try:
                    created_time = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    duration = (
                        datetime.now(timezone.utc) - created_time
                    ).total_seconds() / 60
                    max_duration = workflow_config.get("max_duration_minutes", 30)

                    if duration > max_duration:
                        issues.append(
                            f"Run has been in progress for {duration:.1f} minutes (max: {max_duration})"
                        )
                except:
                    issues.append("Cannot determine run duration")

        # Check for repeated failures
        recent_conclusions = [
            run.get("conclusion") for run in runs[:3] if run.get("conclusion")
        ]
        if recent_conclusions and all(c == "failure" for c in recent_conclusions):
            issues.append(f"Last {len(recent_conclusions)} runs failed")

        # Check for workflow type-specific issues
        workflow_type = workflow_config.get("type", "unknown")
        if workflow_type == "critical" and latest_run.get("conclusion") == "failure":
            issues.append("Critical workflow failed")

        return issues

    def _calculate_workflow_metrics(
        self, workflow: str, runs: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate metrics for workflow performance"""
        if not runs:
            return {}

        # Calculate success rate
        conclusions = [run.get("conclusion") for run in runs if run.get("conclusion")]
        success_rate = (
            conclusions.count("success") / len(conclusions) if conclusions else 0
        )

        # Calculate average duration (approximate)
        durations = []
        for run in runs:
            if run.get("createdAt") and run.get("updatedAt"):
                try:
                    created = datetime.fromisoformat(
                        run["createdAt"].replace("Z", "+00:00")
                    )
                    updated = datetime.fromisoformat(
                        run["updatedAt"].replace("Z", "+00:00")
                    )
                    duration = (updated - created).total_seconds() / 60
                    durations.append(duration)
                except:
                    continue

        avg_duration = sum(durations) / len(durations) if durations else 0

        # Count runs by status
        status_counts = {}
        for run in runs:
            status = run.get("conclusion") or run.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "success_rate": round(success_rate, 2),
            "average_duration_minutes": round(avg_duration, 1),
            "total_runs": len(runs),
            "status_distribution": status_counts,
            "last_success": self._find_last_successful_run(runs),
            "failure_streak": self._calculate_failure_streak(runs),
        }

    def _find_last_successful_run(self, runs: List[Dict]) -> Optional[str]:
        """Find the timestamp of the last successful run"""
        for run in runs:
            if run.get("conclusion") == "success":
                return run.get("updatedAt")
        return None

    def _calculate_failure_streak(self, runs: List[Dict]) -> int:
        """Calculate current failure streak"""
        streak = 0
        for run in runs:
            if run.get("conclusion") == "failure":
                streak += 1
            elif run.get("conclusion") == "success":
                break
        return streak

    def validate_workflow_dependencies(self, workflow: str) -> Tuple[bool, List[str]]:
        """Validate that workflow dependencies are satisfied"""
        if workflow not in self.workflow_graph:
            return False, [f"Unknown workflow: {workflow}"]

        issues = []
        dependencies = self.workflow_graph[workflow]["depends_on"]

        for dep in dependencies:
            dep_status = self.get_workflow_status(dep)

            # Check if dependency is healthy
            if dep_status["health"] == "unhealthy":
                issues.append(f"Dependency {dep} is unhealthy")

            # Check if dependency is currently running
            if dep_status["status"] == "in_progress":
                issues.append(f"Dependency {dep} is currently running")

            # Check if dependency's last run failed
            if dep_status.get("conclusion") == "failure":
                issues.append(f"Dependency {dep} failed in last run")

        return len(issues) == 0, issues

    def check_workflow_sequencing(self) -> Dict[str, List[str]]:
        """Check if workflows are running in proper sequence"""
        sequencing_issues = {}

        for workflow in self.workflow_graph.keys():
            issues = []
            workflow_status = self.get_workflow_status(workflow)

            # Skip if workflow is not running
            if workflow_status["status"] != "in_progress":
                continue

            # Check dependencies
            dependencies = self.workflow_graph[workflow]["depends_on"]
            for dep in dependencies:
                dep_status = self.get_workflow_status(dep)

                # Issue if dependency is also running
                if dep_status["status"] == "in_progress":
                    issues.append(f"Running concurrently with dependency {dep}")

                # Issue if dependency hasn't completed successfully
                elif dep_status.get("conclusion") != "success":
                    issues.append(f"Running despite dependency {dep} not successful")

            if issues:
                sequencing_issues[workflow] = issues

        return sequencing_issues

    def get_system_state_variables(self) -> Dict[str, str]:
        """Get system state variables from GitHub repository"""
        success, output = self._run_gh_command(
            ["variable", "list", "--repo", self.repository, "--json", "name,value"]
        )

        if success:
            try:
                variables = json.loads(output)
                return {var["name"]: var["value"] for var in variables}
            except json.JSONDecodeError:
                return {}
        return {}

    def check_system_state_consistency(self) -> Dict[str, Any]:
        """Check consistency of system state across workflows"""
        variables = self.get_system_state_variables()

        consistency_checks = {
            "deployment_state": self._check_deployment_state_consistency(variables),
            "circuit_breaker_state": self._check_circuit_breaker_consistency(variables),
            "recovery_state": self._check_recovery_state_consistency(variables),
            "orchestration_state": self._check_orchestration_state_consistency(
                variables
            ),
        }

        return consistency_checks

    def _check_deployment_state_consistency(
        self, variables: Dict[str, str]
    ) -> Dict[str, Any]:
        """Check deployment state consistency"""
        deployed_digest = variables.get("DEPLOYED_ARTIFACT_DIGEST", "")
        deployment_status = variables.get("DEPLOYMENT_STATUS", "")
        deployment_in_progress = variables.get("DEPLOYMENT_IN_PROGRESS", "false")
        deployment_started_at = variables.get("DEPLOYMENT_STARTED_AT", "")

        issues = []

        # Check for stuck deployment
        if deployment_in_progress == "true" and deployment_started_at:
            try:
                started_time = datetime.fromisoformat(
                    deployment_started_at.replace("Z", "+00:00")
                )
                duration = (
                    datetime.now(timezone.utc) - started_time
                ).total_seconds() / 60
                if duration > 45:  # 45 minutes
                    issues.append(f"Deployment stuck for {duration:.1f} minutes")
            except:
                issues.append("Invalid deployment start timestamp")

        # Check for inconsistent state
        if not deployed_digest and deployment_status == "successful":
            issues.append("Deployment marked successful but no artifact digest")

        return {
            "status": "consistent" if not issues else "inconsistent",
            "issues": issues,
            "deployed_digest": (
                deployed_digest[:12] + "..." if deployed_digest else "none"
            ),
            "deployment_in_progress": deployment_in_progress == "true",
            "deployment_status": deployment_status,
        }

    def _check_circuit_breaker_consistency(
        self, variables: Dict[str, str]
    ) -> Dict[str, Any]:
        """Check circuit breaker state consistency"""
        cb_status = variables.get("CIRCUIT_BREAKER_STATUS", "closed")
        recovery_failures = int(variables.get("RECOVERY_FAILURE_COUNT", "0"))
        deployment_failures = int(variables.get("DEPLOYMENT_FAILURE_COUNT", "0"))
        recovery_threshold = int(variables.get("CIRCUIT_BREAKER_THRESHOLD", "3"))
        deployment_threshold = int(
            variables.get("DEPLOYMENT_CIRCUIT_BREAKER_THRESHOLD", "5")
        )

        issues = []

        # Check if circuit breaker should be open
        should_be_open = (
            recovery_failures >= recovery_threshold
            or deployment_failures >= deployment_threshold
        )

        if should_be_open and cb_status != "open":
            issues.append(
                f"Circuit breaker should be open (R:{recovery_failures}/{recovery_threshold}, D:{deployment_failures}/{deployment_threshold})"
            )

        if cb_status == "open" and not should_be_open:
            issues.append("Circuit breaker open but failure counts below thresholds")

        return {
            "status": "consistent" if not issues else "inconsistent",
            "issues": issues,
            "circuit_breaker_status": cb_status,
            "recovery_failures": f"{recovery_failures}/{recovery_threshold}",
            "deployment_failures": f"{deployment_failures}/{deployment_threshold}",
        }

    def _check_recovery_state_consistency(
        self, variables: Dict[str, str]
    ) -> Dict[str, Any]:
        """Check recovery state consistency"""
        recovery_session = variables.get("RECOVERY_SESSION_ID", "")
        recovery_start = variables.get("RECOVERY_START_TIME", "")

        issues = []

        # Check for stuck recovery
        if recovery_session and recovery_start:
            try:
                start_time = datetime.fromisoformat(
                    recovery_start.replace("Z", "+00:00")
                )
                duration = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() / 60
                if duration > 20:  # 20 minutes
                    issues.append(f"Recovery session stuck for {duration:.1f} minutes")
            except:
                issues.append("Invalid recovery start timestamp")

        return {
            "status": "consistent" if not issues else "inconsistent",
            "issues": issues,
            "recovery_in_progress": bool(recovery_session),
            "recovery_session_id": (
                recovery_session[:16] + "..." if recovery_session else "none"
            ),
        }

    def _check_orchestration_state_consistency(
        self, variables: Dict[str, str]
    ) -> Dict[str, Any]:
        """Check orchestration state consistency"""
        orchestration_session = variables.get("ORCHESTRATION_SESSION_ID", "")
        orchestration_start = variables.get("ORCHESTRATION_START_TIME", "")
        last_orchestration = variables.get("LAST_COMPLETED_ORCHESTRATION", "")

        issues = []

        # Check for stuck orchestration
        if orchestration_session and orchestration_start:
            try:
                start_time = datetime.fromisoformat(
                    orchestration_start.replace("Z", "+00:00")
                )
                duration = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() / 60
                if duration > 15:  # 15 minutes
                    issues.append(
                        f"Orchestration session stuck for {duration:.1f} minutes"
                    )
            except:
                issues.append("Invalid orchestration start timestamp")

        return {
            "status": "consistent" if not issues else "inconsistent",
            "issues": issues,
            "orchestration_in_progress": bool(orchestration_session),
            "last_orchestration": last_orchestration,
        }

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive workflow status report"""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repository": self.repository,
            "workflow_statuses": {},
            "dependency_validation": {},
            "sequencing_issues": {},
            "system_consistency": {},
            "overall_health": "unknown",
            "critical_issues": [],
            "warnings": [],
            "recommendations": [],
        }

        # Get status for all workflows
        for workflow in self.workflow_graph.keys():
            report["workflow_statuses"][workflow] = self.get_workflow_status(workflow)

        # Validate dependencies
        for workflow in self.workflow_graph.keys():
            valid, issues = self.validate_workflow_dependencies(workflow)
            report["dependency_validation"][workflow] = {
                "valid": valid,
                "issues": issues,
            }

        # Check sequencing
        report["sequencing_issues"] = self.check_workflow_sequencing()

        # Check system consistency
        report["system_consistency"] = self.check_system_state_consistency()

        # Analyze overall health and generate recommendations
        self._analyze_overall_health(report)

        return report

    def _analyze_overall_health(self, report: Dict[str, Any]) -> None:
        """Analyze overall system health and generate recommendations"""
        critical_issues = []
        warnings = []
        recommendations = []

        # Check workflow health
        unhealthy_workflows = []
        degraded_workflows = []

        for workflow, status in report["workflow_statuses"].items():
            health = status.get("health", "unknown")
            workflow_type = self.workflow_graph.get(workflow, {}).get("type", "unknown")

            if health == "unhealthy":
                unhealthy_workflows.append(workflow)
                if workflow_type == "critical":
                    critical_issues.append(f"Critical workflow {workflow} is unhealthy")
                else:
                    warnings.append(f"Workflow {workflow} is unhealthy")
            elif health == "degraded":
                degraded_workflows.append(workflow)
                warnings.append(f"Workflow {workflow} is degraded")

            # Check for specific issues
            issues = status.get("issues", [])
            for issue in issues:
                if "stuck" in issue.lower() or "failed" in issue.lower():
                    if workflow_type == "critical":
                        critical_issues.append(f"{workflow}: {issue}")
                    else:
                        warnings.append(f"{workflow}: {issue}")

        # Check dependency issues
        for workflow, validation in report["dependency_validation"].items():
            if not validation["valid"]:
                workflow_type = self.workflow_graph.get(workflow, {}).get(
                    "type", "unknown"
                )
                for issue in validation["issues"]:
                    if workflow_type == "critical":
                        critical_issues.append(f"{workflow} dependency issue: {issue}")
                    else:
                        warnings.append(f"{workflow} dependency issue: {issue}")

        # Check sequencing issues
        if report["sequencing_issues"]:
            for workflow, issues in report["sequencing_issues"].items():
                for issue in issues:
                    warnings.append(f"{workflow} sequencing: {issue}")

        # Check system consistency
        consistency = report["system_consistency"]
        for check_name, check_result in consistency.items():
            if (
                isinstance(check_result, dict)
                and check_result.get("status") == "inconsistent"
            ):
                for issue in check_result.get("issues", []):
                    if "stuck" in issue.lower():
                        critical_issues.append(f"{check_name}: {issue}")
                    else:
                        warnings.append(f"{check_name}: {issue}")

        # Determine overall health
        if critical_issues:
            overall_health = "critical"
        elif warnings:
            overall_health = "warning"
        elif unhealthy_workflows or degraded_workflows:
            overall_health = "degraded"
        else:
            overall_health = "healthy"

        # Generate recommendations
        if critical_issues:
            recommendations.append("Immediate attention required for critical issues")
            recommendations.append("Consider triggering emergency coordination")

        if unhealthy_workflows:
            recommendations.append(
                f'Investigate unhealthy workflows: {", ".join(unhealthy_workflows)}'
            )

        if degraded_workflows:
            recommendations.append(
                f'Monitor degraded workflows: {", ".join(degraded_workflows)}'
            )

        # Check for stuck processes
        deployment_state = consistency.get("deployment_state", {})
        if deployment_state.get("deployment_in_progress"):
            recommendations.append("Consider clearing stuck deployment lock")

        recovery_state = consistency.get("recovery_state", {})
        if recovery_state.get("recovery_in_progress"):
            recommendations.append("Consider clearing stuck recovery session")

        if not critical_issues and not warnings:
            recommendations.append("All workflows and system state appear healthy")

        # Update report
        report["overall_health"] = overall_health
        report["critical_issues"] = critical_issues
        report["warnings"] = warnings
        report["recommendations"] = recommendations

    def export_report(self, report: Dict[str, Any], output_file: str) -> None:
        """Export report to JSON file"""
        try:
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
            print(f"Report exported to {output_file}")
        except Exception as e:
            print(f"Error exporting report: {e}")

    def print_summary(self, report: Dict[str, Any]) -> None:
        """Print a summary of the workflow status report"""
        print("=" * 80)
        print("🎼 Workflow Status Monitor Report")
        print("=" * 80)
        print(f"Repository: {report['repository']}")
        print(f"Timestamp: {report['timestamp']}")
        print(f"Overall Health: {report['overall_health'].upper()}")
        print()

        # Workflow statuses
        print("📊 Workflow Health:")
        for workflow, status in report["workflow_statuses"].items():
            health = status.get("health", "unknown")
            health_emoji = {
                "healthy": "✅",
                "degraded": "⚠️",
                "unhealthy": "❌",
                "unknown": "❓",
            }.get(health, "❓")

            workflow_status = status.get("status", "unknown")
            print(
                f"  {health_emoji} {workflow}: {health.upper()} (last: {workflow_status})"
            )

        print()

        # Critical issues
        if report["critical_issues"]:
            print("🚨 Critical Issues:")
            for issue in report["critical_issues"]:
                print(f"  - {issue}")
            print()

        # Warnings
        if report["warnings"]:
            print("⚠️  Warnings:")
            for warning in report["warnings"][:10]:  # Show first 10
                print(f"  - {warning}")
            if len(report["warnings"]) > 10:
                print(f"  ... and {len(report['warnings']) - 10} more")
            print()

        # Recommendations
        if report["recommendations"]:
            print("💡 Recommendations:")
            for rec in report["recommendations"][:5]:  # Show first 5
                print(f"  - {rec}")
            if len(report["recommendations"]) > 5:
                print(f"  ... and {len(report['recommendations']) - 5} more")

        print("=" * 80)


def main():
    """Main CLI interface for workflow status monitoring"""
    parser = argparse.ArgumentParser(
        description="Monitor CI/CD workflow status and health"
    )
    parser.add_argument("--repo", required=True, help="GitHub repository (owner/repo)")
    parser.add_argument("--workflow", help="Specific workflow to check")
    parser.add_argument("--export", help="Export report to JSON file")
    parser.add_argument("--summary", action="store_true", help="Show summary only")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--check-dependencies", action="store_true", help="Check workflow dependencies"
    )
    parser.add_argument(
        "--check-sequencing", action="store_true", help="Check workflow sequencing"
    )
    parser.add_argument(
        "--check-consistency",
        action="store_true",
        help="Check system state consistency",
    )

    args = parser.parse_args()

    try:
        monitor = WorkflowStatusMonitor(args.repo)

        if args.workflow:
            # Check specific workflow
            status = monitor.get_workflow_status(args.workflow)
            if args.json:
                print(json.dumps(status, indent=2))
            else:
                print(f"Workflow: {args.workflow}")
                print(f"Status: {status.get('status', 'unknown')}")
                print(f"Health: {status.get('health', 'unknown')}")
                print(f"Issues: {len(status.get('issues', []))}")
                for issue in status.get("issues", []):
                    print(f"  - {issue}")

        elif args.check_dependencies:
            # Check dependencies for all workflows
            for workflow in monitor.workflow_graph.keys():
                valid, issues = monitor.validate_workflow_dependencies(workflow)
                print(f"{workflow}: {'✅ Valid' if valid else '❌ Issues'}")
                for issue in issues:
                    print(f"  - {issue}")

        elif args.check_sequencing:
            # Check workflow sequencing
            issues = monitor.check_workflow_sequencing()
            if issues:
                print("Sequencing Issues:")
                for workflow, workflow_issues in issues.items():
                    print(f"{workflow}:")
                    for issue in workflow_issues:
                        print(f"  - {issue}")
            else:
                print("✅ No sequencing issues detected")

        elif args.check_consistency:
            # Check system state consistency
            consistency = monitor.check_system_state_consistency()
            for check_name, result in consistency.items():
                status = result.get("status", "unknown")
                print(
                    f"{check_name}: {'✅ Consistent' if status == 'consistent' else '❌ Inconsistent'}"
                )
                for issue in result.get("issues", []):
                    print(f"  - {issue}")

        else:
            # Generate comprehensive report
            report = monitor.generate_comprehensive_report()

            if args.json:
                print(json.dumps(report, indent=2))
            elif args.summary:
                monitor.print_summary(report)
            else:
                monitor.print_summary(report)
                if args.export:
                    monitor.export_report(report, args.export)

        # Exit with appropriate code
        if args.workflow:
            health = monitor.get_workflow_status(args.workflow).get("health", "unknown")
            sys.exit(0 if health in ["healthy", "degraded"] else 1)
        else:
            report = monitor.generate_comprehensive_report()
            overall_health = report.get("overall_health", "unknown")
            sys.exit(0 if overall_health in ["healthy", "warning", "degraded"] else 1)

    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
