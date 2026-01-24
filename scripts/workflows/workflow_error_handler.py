#!/usr/bin/env python3
"""
Workflow Error Handler - Comprehensive error handling and recovery coordination.

This script provides functionality for:
- Detecting and categorizing workflow errors
- Coordinating error recovery across workflows
- Managing error escalation and notifications
- Tracking error patterns and trends
- Implementing error-based circuit breaker logic

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


class WorkflowErrorHandler:
    """Handles workflow errors and coordinates recovery actions."""

    def __init__(self, repository: str):
        self.repository = repository
        self.gh_token = os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')
        if not self.gh_token:
            raise ValueError("GitHub token not found. Set GITHUB_TOKEN or GH_TOKEN environment variable.")
        
        # Error classification patterns
        self.error_patterns = {
            'infrastructure': [
                'timeout', 'connection refused', 'network error', 'dns resolution',
                'docker daemon', 'container runtime', 'resource exhausted'
            ],
            'dependency': [
                'dependency failed', 'upstream failure', 'prerequisite not met',
                'required service unavailable', 'integration test failed'
            ],
            'configuration': [
                'invalid configuration', 'missing environment variable',
                'authentication failed', 'permission denied', 'invalid credentials'
            ],
            'application': [
                'test failed', 'compilation error', 'runtime error',
                'assertion failed', 'validation error'
            ],
            'deployment': [
                'deployment failed', 'rollback failed', 'health check failed',
                'service unavailable', 'artifact not found'
            ]
        }
        
        # Recovery strategies by error type
        self.recovery_strategies = {
            'infrastructure': ['retry', 'resource_cleanup', 'escalate'],
            'dependency': ['wait_and_retry', 'skip_optional', 'escalate'],
            'configuration': ['validate_config', 'reset_credentials', 'escalate'],
            'application': ['rerun_tests', 'rollback', 'escalate'],
            'deployment': ['retry_deployment', 'rollback', 'emergency_stop']
        }

    def _run_gh_command(self, command: List[str]) -> Tuple[bool, str]:
        """Run a GitHub CLI command and return success status and output"""
        try:
            env = os.environ.copy()
            env['GH_TOKEN'] = self.gh_token
            
            result = subprocess.run(
                ['gh'] + command,
                capture_output=True,
                text=True,
                env=env,
                timeout=60
            )
            
            return result.returncode == 0, result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def get_failed_workflow_runs(self, hours: int = 24) -> List[Dict]:
        """Get failed workflow runs from the last N hours"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        success, output = self._run_gh_command([
            'run', 'list',
            '--limit', '100',
            '--json', 'databaseId,status,conclusion,createdAt,workflowName,displayTitle,headSha'
        ])
        
        if not success:
            return []
        
        try:
            all_runs = json.loads(output)
            failed_runs = []
            
            for run in all_runs:
                if run.get('conclusion') == 'failure':
                    try:
                        created_at = datetime.fromisoformat(run['createdAt'].replace('Z', '+00:00'))
                        if created_at > cutoff_time:
                            failed_runs.append(run)
                    except:
                        continue
            
            return failed_runs
        except json.JSONDecodeError:
            return []

    def get_workflow_run_logs(self, run_id: str) -> Dict[str, Any]:
        """Get logs for a specific workflow run"""
        success, output = self._run_gh_command([
            'run', 'view', run_id, '--log-failed'
        ])
        
        if success:
            return {
                'run_id': run_id,
                'logs': output,
                'retrieved_at': datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                'run_id': run_id,
                'logs': '',
                'error': output,
                'retrieved_at': datetime.now(timezone.utc).isoformat()
            }

    def classify_error(self, error_text: str) -> Tuple[str, float]:
        """Classify error based on text patterns and return category with confidence"""
        error_text_lower = error_text.lower()
        
        category_scores = {}
        
        for category, patterns in self.error_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in error_text_lower:
                    score += 1
            
            if score > 0:
                category_scores[category] = score / len(patterns)
        
        if not category_scores:
            return 'unknown', 0.0
        
        best_category = max(category_scores.items(), key=lambda x: x[1])
        return best_category[0], best_category[1]

    def analyze_error_patterns(self, failed_runs: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns in failed workflow runs"""
        if not failed_runs:
            return {
                'total_failures': 0,
                'error_categories': {},
                'workflow_failure_rates': {},
                'time_distribution': {},
                'patterns': []
            }
        
        error_categories = {}
        workflow_failures = {}
        hourly_distribution = {}
        
        for run in failed_runs:
            workflow_name = run.get('workflowName', 'unknown')
            workflow_failures[workflow_name] = workflow_failures.get(workflow_name, 0) + 1
            
            # Get hour for time distribution
            try:
                created_at = datetime.fromisoformat(run['createdAt'].replace('Z', '+00:00'))
                hour = created_at.hour
                hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
            except:
                pass
            
            # Classify error if we have logs
            run_id = str(run.get('databaseId', ''))
            if run_id:
                logs = self.get_workflow_run_logs(run_id)
                if logs.get('logs'):
                    category, confidence = self.classify_error(logs['logs'])
                    if category not in error_categories:
                        error_categories[category] = {'count': 0, 'confidence_sum': 0}
                    error_categories[category]['count'] += 1
                    error_categories[category]['confidence_sum'] += confidence
        
        # Calculate average confidence for each category
        for category in error_categories:
            count = error_categories[category]['count']
            error_categories[category]['avg_confidence'] = error_categories[category]['confidence_sum'] / count
            del error_categories[category]['confidence_sum']
        
        # Identify patterns
        patterns = []
        
        # High failure rate pattern
        total_runs = len(failed_runs)
        if total_runs > 10:
            patterns.append(f"High failure volume: {total_runs} failures detected")
        
        # Workflow-specific patterns
        for workflow, count in workflow_failures.items():
            if count > 3:
                patterns.append(f"Repeated failures in {workflow}: {count} failures")
        
        # Time-based patterns
        if hourly_distribution:
            peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])
            if peak_hour[1] > total_runs * 0.3:  # More than 30% of failures in one hour
                patterns.append(f"Failure spike at hour {peak_hour[0]}: {peak_hour[1]} failures")
        
        return {
            'total_failures': total_runs,
            'error_categories': error_categories,
            'workflow_failure_rates': workflow_failures,
            'time_distribution': hourly_distribution,
            'patterns': patterns
        }

    def recommend_recovery_actions(self, error_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recommend recovery actions based on error analysis"""
        recommendations = []
        
        error_categories = error_analysis.get('error_categories', {})
        workflow_failures = error_analysis.get('workflow_failure_rates', {})
        total_failures = error_analysis.get('total_failures', 0)
        
        # Recommendations based on error categories
        for category, data in error_categories.items():
            count = data.get('count', 0)
            confidence = data.get('avg_confidence', 0)
            
            if count > 2 and confidence > 0.3:  # Significant pattern
                strategies = self.recovery_strategies.get(category, ['escalate'])
                
                for strategy in strategies:
                    recommendations.append({
                        'action': strategy,
                        'reason': f'{count} {category} errors detected (confidence: {confidence:.2f})',
                        'priority': 'high' if count > 5 else 'medium',
                        'category': category,
                        'automated': strategy in ['retry', 'resource_cleanup', 'wait_and_retry']
                    })
        
        # Recommendations based on workflow patterns
        for workflow, count in workflow_failures.items():
            if count > 5:
                recommendations.append({
                    'action': 'investigate_workflow',
                    'reason': f'{workflow} has {count} failures - needs investigation',
                    'priority': 'high',
                    'category': 'workflow_specific',
                    'automated': False,
                    'workflow': workflow
                })
        
        # System-wide recommendations
        if total_failures > 20:
            recommendations.append({
                'action': 'emergency_coordination',
                'reason': f'High failure volume: {total_failures} failures',
                'priority': 'critical',
                'category': 'system_wide',
                'automated': True
            })
        
        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 3))
        
        return recommendations

    def execute_automated_recovery(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute automated recovery action"""
        action = recommendation.get('action')
        result = {
            'action': action,
            'executed_at': datetime.now(timezone.utc).isoformat(),
            'success': False,
            'details': '',
            'recommendation': recommendation
        }
        
        try:
            if action == 'retry':
                # Trigger retry of failed workflow
                workflow = recommendation.get('workflow')
                if workflow:
                    success, output = self._run_gh_command([
                        'workflow', 'run', f'{workflow}.yml',
                        '--repo', self.repository
                    ])
                    result['success'] = success
                    result['details'] = output
                else:
                    result['details'] = 'No workflow specified for retry'
            
            elif action == 'resource_cleanup':
                # Clear stuck processes
                success = self._clear_stuck_processes()
                result['success'] = success
                result['details'] = 'Attempted to clear stuck processes'
            
            elif action == 'wait_and_retry':
                # Wait and then retry (implemented as delayed trigger)
                result['success'] = True
                result['details'] = 'Scheduled delayed retry (not implemented in this demo)'
            
            elif action == 'emergency_coordination':
                # Trigger emergency coordination
                success, output = self._run_gh_command([
                    'workflow', 'run', 'workflow-orchestrator.yml',
                    '--repo', self.repository,
                    '--field', 'orchestration_action=emergency-coordination',
                    '--field', 'force_coordination=true'
                ])
                result['success'] = success
                result['details'] = output
            
            else:
                result['details'] = f'Automated execution not implemented for action: {action}'
        
        except Exception as e:
            result['details'] = f'Error executing {action}: {str(e)}'
        
        return result

    def _clear_stuck_processes(self) -> bool:
        """Clear stuck deployment and recovery processes"""
        try:
            # Clear stuck deployment
            self._run_gh_command([
                'variable', 'set', 'DEPLOYMENT_IN_PROGRESS',
                '--body', 'false',
                '--repo', self.repository
            ])
            
            # Clear stuck recovery session
            self._run_gh_command([
                'variable', 'delete', 'RECOVERY_SESSION_ID',
                '--repo', self.repository
            ])
            
            # Clear stuck orchestration session
            self._run_gh_command([
                'variable', 'delete', 'ORCHESTRATION_SESSION_ID',
                '--repo', self.repository
            ])
            
            return True
        except:
            return False

    def generate_error_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive error analysis report"""
        failed_runs = self.get_failed_workflow_runs(hours)
        error_analysis = self.analyze_error_patterns(failed_runs)
        recommendations = self.recommend_recovery_actions(error_analysis)
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'repository': self.repository,
            'analysis_period_hours': hours,
            'failed_runs': failed_runs,
            'error_analysis': error_analysis,
            'recovery_recommendations': recommendations,
            'summary': {
                'total_failures': error_analysis.get('total_failures', 0),
                'unique_workflows_affected': len(error_analysis.get('workflow_failure_rates', {})),
                'error_categories_detected': len(error_analysis.get('error_categories', {})),
                'automated_actions_available': len([r for r in recommendations if r.get('automated', False)]),
                'manual_actions_required': len([r for r in recommendations if not r.get('automated', False)])
            }
        }

    def print_error_summary(self, report: Dict[str, Any]) -> None:
        """Print a summary of the error analysis report"""
        print("=" * 80)
        print("🚨 Workflow Error Analysis Report")
        print("=" * 80)
        print(f"Repository: {report['repository']}")
        print(f"Analysis Period: {report['analysis_period_hours']} hours")
        print(f"Timestamp: {report['timestamp']}")
        print()
        
        summary = report.get('summary', {})
        print("📊 Summary:")
        print(f"  Total Failures: {summary.get('total_failures', 0)}")
        print(f"  Workflows Affected: {summary.get('unique_workflows_affected', 0)}")
        print(f"  Error Categories: {summary.get('error_categories_detected', 0)}")
        print(f"  Automated Actions Available: {summary.get('automated_actions_available', 0)}")
        print(f"  Manual Actions Required: {summary.get('manual_actions_required', 0)}")
        print()
        
        # Error categories
        error_analysis = report.get('error_analysis', {})
        error_categories = error_analysis.get('error_categories', {})
        if error_categories:
            print("🏷️  Error Categories:")
            for category, data in error_categories.items():
                count = data.get('count', 0)
                confidence = data.get('avg_confidence', 0)
                print(f"  - {category}: {count} errors (confidence: {confidence:.2f})")
            print()
        
        # Workflow failures
        workflow_failures = error_analysis.get('workflow_failure_rates', {})
        if workflow_failures:
            print("⚙️  Workflow Failure Rates:")
            for workflow, count in sorted(workflow_failures.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {workflow}: {count} failures")
            print()
        
        # Patterns
        patterns = error_analysis.get('patterns', [])
        if patterns:
            print("🔍 Detected Patterns:")
            for pattern in patterns:
                print(f"  - {pattern}")
            print()
        
        # Recommendations
        recommendations = report.get('recovery_recommendations', [])
        if recommendations:
            print("💡 Recovery Recommendations:")
            for i, rec in enumerate(recommendations[:10], 1):  # Show first 10
                priority = rec.get('priority', 'medium')
                action = rec.get('action', 'unknown')
                reason = rec.get('reason', 'No reason provided')
                automated = "🤖 Automated" if rec.get('automated', False) else "👤 Manual"
                
                priority_emoji = {
                    'critical': '🚨',
                    'high': '⚠️',
                    'medium': 'ℹ️',
                    'low': '💡'
                }.get(priority, 'ℹ️')
                
                print(f"  {i}. {priority_emoji} {action} ({automated})")
                print(f"     {reason}")
            
            if len(recommendations) > 10:
                print(f"     ... and {len(recommendations) - 10} more recommendations")
        
        print("=" * 80)


def main():
    """Main CLI interface for workflow error handling"""
    parser = argparse.ArgumentParser(description="Handle and analyze CI/CD workflow errors")
    parser.add_argument('--repo', required=True, help='GitHub repository (owner/repo)')
    parser.add_argument('--hours', type=int, default=24, help='Hours of history to analyze')
    parser.add_argument('--export', help='Export report to JSON file')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--execute-automated', action='store_true', help='Execute automated recovery actions')
    parser.add_argument('--run-id', help='Analyze specific workflow run')
    
    args = parser.parse_args()
    
    try:
        handler = WorkflowErrorHandler(args.repo)
        
        if args.run_id:
            # Analyze specific run
            logs = handler.get_workflow_run_logs(args.run_id)
            if logs.get('logs'):
                category, confidence = handler.classify_error(logs['logs'])
                result = {
                    'run_id': args.run_id,
                    'error_category': category,
                    'confidence': confidence,
                    'logs_retrieved': bool(logs.get('logs')),
                    'analysis_timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                if args.json:
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Run ID: {args.run_id}")
                    print(f"Error Category: {category}")
                    print(f"Confidence: {confidence:.2f}")
            else:
                print(f"Could not retrieve logs for run {args.run_id}")
                sys.exit(1)
        
        else:
            # Generate comprehensive report
            report = handler.generate_error_report(args.hours)
            
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                handler.print_error_summary(report)
            
            if args.export:
                with open(args.export, 'w') as f:
                    json.dump(report, f, indent=2)
                print(f"\nReport exported to {args.export}")
            
            # Execute automated recovery actions if requested
            if args.execute_automated:
                recommendations = report.get('recovery_recommendations', [])
                automated_recs = [r for r in recommendations if r.get('automated', False)]
                
                if automated_recs:
                    print(f"\n🤖 Executing {len(automated_recs)} automated recovery actions...")
                    
                    for rec in automated_recs:
                        print(f"Executing: {rec.get('action')} - {rec.get('reason')}")
                        result = handler.execute_automated_recovery(rec)
                        
                        if result['success']:
                            print(f"  ✅ Success: {result.get('details', 'No details')}")
                        else:
                            print(f"  ❌ Failed: {result.get('details', 'No details')}")
                else:
                    print("\n🤖 No automated recovery actions available")
            
            # Exit with appropriate code based on error severity
            total_failures = report.get('summary', {}).get('total_failures', 0)
            critical_recs = len([r for r in report.get('recovery_recommendations', []) if r.get('priority') == 'critical'])
            
            if critical_recs > 0:
                sys.exit(2)  # Critical issues
            elif total_failures > 10:
                sys.exit(1)  # High failure rate
            else:
                sys.exit(0)  # Normal
    
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()