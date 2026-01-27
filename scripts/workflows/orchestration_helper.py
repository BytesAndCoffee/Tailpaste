#!/usr/bin/env python3
"""
Helper script for workflow orchestration analysis.
"""

import json
import sys
from datetime import datetime, timezone


def get_unhealthy_workflows():
    """Get list of unhealthy workflows."""
    try:
        with open("orchestration_report.json") as f:
            report = json.load(f)

        unhealthy = []
        for workflow, state in report.get("workflow_states", {}).items():
            if state.get("health") == "unhealthy":
                unhealthy.append(workflow)

        print(",".join(unhealthy))
    except FileNotFoundError:
        print("", file=sys.stderr)
        sys.stderr.write("Warning: orchestration_report.json not found\n")
    except json.JSONDecodeError as e:
        print("", file=sys.stderr)
        sys.stderr.write(f"Error: Invalid JSON in orchestration_report.json: {e}\n")
    except Exception as e:
        print("", file=sys.stderr)
        sys.stderr.write(f"Error getting unhealthy workflows: {e}\n")


def calculate_stuck_duration(timestamp_str):
    """Calculate duration since timestamp."""
    try:
        start_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        print(int(duration))
    except ValueError as e:
        sys.stderr.write(f"Error: Invalid timestamp format '{timestamp_str}': {e}\n")
        print(0)
    except Exception as e:
        sys.stderr.write(f"Error calculating stuck duration: {e}\n")
        print(0)


def get_critical_recommendations():
    """Get critical recommendations."""
    try:
        with open("orchestration_report.json") as f:
            report = json.load(f)

        critical_recs = [
            r for r in report.get("recommendations", []) if "CRITICAL:" in r
        ]
        for rec in critical_recs:
            print(f"- {rec}")
    except FileNotFoundError:
        sys.stderr.write("Warning: orchestration_report.json not found\n")
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Error: Invalid JSON in orchestration_report.json: {e}\n")
    except Exception as e:
        sys.stderr.write(f"Error getting critical recommendations: {e}\n")


def generate_workflow_health_summary():
    """Generate workflow health summary for GitHub step summary."""
    try:
        with open("orchestration_report.json") as f:
            report = json.load(f)

        for workflow, state in report.get("workflow_states", {}).items():
            health = state.get("health", "unknown")
            status = state.get("status", "unknown")

            health_emoji = {
                "healthy": "✅",
                "degraded": "⚠️",
                "unhealthy": "❌",
                "unknown": "❓",
            }.get(health, "❓")

            print(f"- **{workflow}**: {health_emoji} {health.upper()} (last: {status})")
    except FileNotFoundError:
        sys.stderr.write("Warning: orchestration_report.json not found\n")
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Error: Invalid JSON in orchestration_report.json: {e}\n")
    except Exception as e:
        sys.stderr.write(f"Error generating workflow health summary: {e}\n")


def generate_consistency_summary():
    """Generate system consistency summary."""
    try:
        with open("orchestration_report.json") as f:
            report = json.load(f)

        consistency = report.get("system_consistency", {})
        if "error" in consistency:
            print(f'- **Status**: ❌ Error - {consistency["error"]}')
        else:
            for check_name, check_result in consistency.items():
                if isinstance(check_result, dict):
                    status = check_result.get("status", "unknown")
                    status_emoji = "✅" if status == "consistent" else "❌"
                    print(
                        f'- **{check_name.replace("_", " ").title()}**: {status_emoji} {status.upper()}'
                    )

                    issues = check_result.get("issues", [])
                    if issues:
                        for issue in issues[:3]:  # Show first 3 issues
                            print(f"  - {issue}")
    except FileNotFoundError:
        sys.stderr.write("Warning: orchestration_report.json not found\n")
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Error: Invalid JSON in orchestration_report.json: {e}\n")
    except Exception as e:
        sys.stderr.write(f"Error generating consistency summary: {e}\n")


def generate_recommendations_summary():
    """Generate recommendations summary."""
    try:
        with open("orchestration_report.json") as f:
            report = json.load(f)

        recommendations = report.get("recommendations", [])
        for i, rec in enumerate(
            recommendations[:10], 1
        ):  # Show first 10 recommendations
            if "CRITICAL:" in rec:
                print(f"{i}. 🚨 {rec}")
            elif "WARNING:" in rec:
                print(f"{i}. ⚠️ {rec}")
            else:
                print(f"{i}. ℹ️ {rec}")
    except FileNotFoundError:
        sys.stderr.write("Warning: orchestration_report.json not found\n")
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Error: Invalid JSON in orchestration_report.json: {e}\n")
    except Exception as e:
        sys.stderr.write(f"Error generating recommendations summary: {e}\n")


def sync_state():
    """Synchronize state across workflows."""
    try:
        import subprocess
        import os

        def set_variable(name, value):
            cmd = [
                "gh",
                "variable",
                "set",
                name,
                "--body",
                value,
                "--repo",
                os.getenv("GITHUB_REPOSITORY"),
            ]
            subprocess.run(cmd, capture_output=True)

        # Load orchestration report
        with open("orchestration_report.json") as f:
            report = json.load(f)

        # Synchronize key state information
        consistency = report.get("system_consistency", {})

        # Record orchestration results
        set_variable("LAST_ORCHESTRATION_TIMESTAMP", report["timestamp"])
        set_variable("LAST_ORCHESTRATION_SESSION", report["session_id"])

        # Record workflow health summary
        workflow_health = {}
        for workflow, state in report.get("workflow_states", {}).items():
            workflow_health[workflow] = state.get("health", "unknown")

        set_variable("WORKFLOW_HEALTH_SUMMARY", json.dumps(workflow_health))

        # Record critical issues count
        critical_count = len(
            [r for r in report.get("recommendations", []) if "CRITICAL:" in r]
        )
        set_variable("ORCHESTRATION_CRITICAL_ISSUES", str(critical_count))

        print("✅ State synchronization completed")
    except Exception as e:
        print(f"❌ State synchronization failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: orchestration_helper.py <command> [args...]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "unhealthy-workflows":
        get_unhealthy_workflows()
    elif command == "stuck-duration":
        if len(sys.argv) > 2:
            calculate_stuck_duration(sys.argv[2])
        else:
            print(0)
    elif command == "critical-recommendations":
        get_critical_recommendations()
    elif command == "workflow-health-summary":
        generate_workflow_health_summary()
    elif command == "consistency-summary":
        generate_consistency_summary()
    elif command == "sync-state":
        sync_state()
    elif command == "recommendations-summary":
        generate_recommendations_summary()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
