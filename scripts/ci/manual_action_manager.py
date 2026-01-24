#!/usr/bin/env python3
"""
Manual Action Manager - Utility for managing and auditing manual CI/CD actions.

This script provides functionality for:
- Logging and auditing manual actions
- Generating manual action reports
- Validating manual action parameters
- Querying manual action history

Requirements: 11.1, 11.2, 11.3, 11.5
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ManualActionManager:
    """Manages manual action logging, auditing, and reporting."""

    def __init__(self):
        self.manual_actions_file = Path(".manual_actions_history.json")

    def load_manual_actions_history(self) -> Dict:
        """Load manual actions history from file."""
        if self.manual_actions_file.exists():
            try:
                with open(self.manual_actions_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(
                    f"Warning: Could not load manual actions history file: {e}",
                    file=sys.stderr,
                )
        return {"manual_actions": [], "metadata": {"version": "1.0"}}

    def save_manual_actions_history(self, data: Dict) -> None:
        """Save manual actions history to file."""
        try:
            with open(self.manual_actions_file, "w") as f:
                json.dump(data, f, indent=2, sort_keys=True)
        except IOError as e:
            print(
                f"Error: Could not save manual actions history file: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    def validate_manual_action_parameters(
        self,
        action_type: str,
        actor: str,
        reason: str,
        bypass_flags: Dict[str, bool] = None,
    ) -> Tuple[bool, str]:
        """Validate manual action parameters."""
        if not action_type:
            return False, "Action type is required"

        if not actor:
            return False, "Actor is required"

        if not reason or len(reason.strip()) < 5:
            return False, "Reason must be at least 5 characters long"

        # Check for sensitive operations requiring detailed reasons
        bypass_flags = bypass_flags or {}
        sensitive_operations = [
            "bypass_gating",
            "override_circuit_breaker",
            "force_deployment",
            "emergency_rollback",
        ]

        has_sensitive_bypass = any(
            bypass_flags.get(flag, False) for flag in sensitive_operations
        )

        if has_sensitive_bypass and len(reason.strip()) < 20:
            return (
                False,
                "Sensitive operations require detailed reasons (minimum 20 characters)",
            )

        return True, "Manual action parameters are valid"

    def record_manual_action(
        self,
        action_type: str,
        actor: str,
        reason: str,
        repository: str,
        workflow_run_id: str = None,
        artifact_digest: str = None,
        bypass_flags: Dict[str, bool] = None,
        additional_data: Dict = None,
    ) -> str:
        """Record a manual action in history."""
        data = self.load_manual_actions_history()

        action_id = (
            f"manual-{action_type}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        )

        manual_action_record = {
            "id": action_id,
            "action_type": action_type,
            "actor": actor,
            "reason": reason,
            "repository": repository,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "workflow_run_id": workflow_run_id,
            "artifact_digest": artifact_digest,
            "bypass_flags": bypass_flags or {},
            "additional_data": additional_data or {},
            "status": "initiated",
        }

        data["manual_actions"].append(manual_action_record)
        data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"

        self.save_manual_actions_history(data)
        print(f"Recorded manual action: {action_id}")
        return action_id

    def update_manual_action_status(
        self, action_id: str, status: str, outcome: str = None, details: str = None
    ) -> None:
        """Update the status of a manual action."""
        data = self.load_manual_actions_history()

        # Find manual action record
        action_found = False
        for action in data["manual_actions"]:
            if action["id"] == action_id:
                action["status"] = status
                action["updated_at"] = datetime.utcnow().isoformat() + "Z"

                if outcome:
                    action["outcome"] = outcome

                if details:
                    action["details"] = details

                if status in ["completed", "successful"]:
                    action["completed_at"] = datetime.utcnow().isoformat() + "Z"
                elif status == "failed":
                    action["failed_at"] = datetime.utcnow().isoformat() + "Z"

                action_found = True
                print(f"Updated manual action {action_id} status to: {status}")
                break

        if not action_found:
            print(f"Warning: Manual action {action_id} not found", file=sys.stderr)
            return

        data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
        self.save_manual_actions_history(data)

    def get_manual_action_status(self, action_id: str) -> Optional[Dict]:
        """Get the status of a specific manual action."""
        data = self.load_manual_actions_history()

        for action in data["manual_actions"]:
            if action["id"] == action_id:
                return action

        return None

    def get_recent_manual_actions(
        self, repository: str = None, action_type: str = None, limit: int = 20
    ) -> List[Dict]:
        """Get recent manual actions with optional filtering."""
        data = self.load_manual_actions_history()

        # Filter by repository and action type if specified
        filtered_actions = data["manual_actions"]

        if repository:
            filtered_actions = [
                action
                for action in filtered_actions
                if action.get("repository") == repository
            ]

        if action_type:
            filtered_actions = [
                action
                for action in filtered_actions
                if action.get("action_type") == action_type
            ]

        # Sort by timestamp (most recent first)
        filtered_actions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return filtered_actions[:limit]

    def generate_manual_actions_report(
        self, repository: str = None, days: int = 30
    ) -> str:
        """Generate a comprehensive manual actions report."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get recent actions within the specified timeframe
        all_actions = self.get_recent_manual_actions(repository=repository, limit=1000)

        # Filter by date
        recent_actions = [
            action
            for action in all_actions
            if datetime.fromisoformat(
                action.get("timestamp", "").replace("Z", "+00:00")
            )
            > cutoff_date
        ]

        if not recent_actions:
            return f"No manual actions found for repository: {repository or 'all repositories'} in the last {days} days"

        report_lines = [
            f"# Manual Actions Report",
            f"Repository: {repository or 'All repositories'}",
            f"Time Period: Last {days} days",
            f"Generated at: {datetime.utcnow().isoformat()}Z",
            "",
            f"Total manual actions: {len(recent_actions)}",
            "",
        ]

        # Summary statistics
        action_types = {}
        actors = {}
        bypass_usage = {
            "bypass_gating": 0,
            "override_circuit_breaker": 0,
            "force_deployment": 0,
            "emergency_rollback": 0,
        }

        successful_count = 0
        failed_count = 0
        pending_count = 0

        for action in recent_actions:
            # Count action types
            action_type = action.get("action_type", "unknown")
            action_types[action_type] = action_types.get(action_type, 0) + 1

            # Count actors
            actor = action.get("actor", "unknown")
            actors[actor] = actors.get(actor, 0) + 1

            # Count bypass flag usage
            bypass_flags = action.get("bypass_flags", {})
            for flag, count in bypass_usage.items():
                if bypass_flags.get(flag, False):
                    bypass_usage[flag] += 1

            # Count status
            status = action.get("status", "unknown")
            if status in ["completed", "successful"]:
                successful_count += 1
            elif status == "failed":
                failed_count += 1
            else:
                pending_count += 1

        report_lines.extend(
            [
                "## Summary Statistics",
                f"- Successful: {successful_count}",
                f"- Failed: {failed_count}",
                f"- Pending/In Progress: {pending_count}",
                "",
                "### Action Types",
            ]
        )

        for action_type, count in sorted(action_types.items()):
            report_lines.append(f"- {action_type}: {count}")

        report_lines.extend(
            [
                "",
                "### Top Actors",
            ]
        )

        for actor, count in sorted(actors.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]:
            report_lines.append(f"- {actor}: {count}")

        report_lines.extend(
            [
                "",
                "### Safety Override Usage",
            ]
        )

        for flag, count in bypass_usage.items():
            if count > 0:
                report_lines.append(f"- {flag.replace('_', ' ').title()}: {count}")

        # Recent actions details
        report_lines.extend(["", "## Recent Manual Actions", ""])

        for action in recent_actions[:20]:  # Show last 20
            status_emoji = {
                "successful": "✅",
                "completed": "✅",
                "failed": "❌",
                "initiated": "🔄",
                "pending": "⏳",
            }.get(action.get("status", "unknown"), "❓")

            report_lines.extend(
                [
                    f"### {status_emoji} {action['id']}",
                    f"- **Type**: {action.get('action_type', 'unknown')}",
                    f"- **Actor**: {action.get('actor', 'unknown')}",
                    f"- **Status**: {action.get('status', 'unknown')}",
                    f"- **Timestamp**: {action.get('timestamp', 'N/A')}",
                    f"- **Reason**: {action.get('reason', 'N/A')}",
                ]
            )

            if action.get("artifact_digest"):
                report_lines.append(f"- **Artifact**: `{action['artifact_digest']}`")

            if action.get("workflow_run_id"):
                report_lines.append(f"- **Workflow Run**: {action['workflow_run_id']}")

            # Show bypass flags if any were used
            bypass_flags = action.get("bypass_flags", {})
            active_bypasses = [flag for flag, value in bypass_flags.items() if value]
            if active_bypasses:
                report_lines.append(f"- **Bypasses**: {', '.join(active_bypasses)}")

            if action.get("outcome"):
                report_lines.append(f"- **Outcome**: {action['outcome']}")

            if action.get("details"):
                report_lines.append(f"- **Details**: {action['details']}")

            report_lines.append("")

        return "\n".join(report_lines)

    def validate_repository_access(self, repository: str) -> Tuple[bool, str]:
        """Validate that the user has access to the repository."""
        try:
            result = subprocess.run(
                ["gh", "repo", "view", repository],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return True, f"Repository access validated: {repository}"
            else:
                return False, f"Cannot access repository: {repository}"

        except subprocess.TimeoutExpired:
            return False, "Timeout while validating repository access"
        except subprocess.SubprocessError as e:
            return False, f"Error validating repository access: {e}"

    def cleanup_old_manual_actions(self, days_to_keep: int = 180) -> int:
        """Clean up old manual action records to prevent file bloat."""
        data = self.load_manual_actions_history()
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        original_count = len(data["manual_actions"])

        # Keep manual actions newer than cutoff date
        data["manual_actions"] = [
            action
            for action in data["manual_actions"]
            if datetime.fromisoformat(
                action.get("timestamp", "").replace("Z", "+00:00")
            )
            > cutoff_date
        ]

        removed_count = original_count - len(data["manual_actions"])

        if removed_count > 0:
            data["metadata"]["last_cleanup"] = datetime.utcnow().isoformat() + "Z"
            data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
            self.save_manual_actions_history(data)
            print(f"Cleaned up {removed_count} old manual action records")

        return removed_count


def main():
    """Main CLI interface for manual action management."""
    parser = argparse.ArgumentParser(
        description="Manage manual action logging and auditing"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate parameters command
    validate_parser = subparsers.add_parser(
        "validate-parameters", help="Validate manual action parameters"
    )
    validate_parser.add_argument(
        "--action-type", required=True, help="Type of manual action"
    )
    validate_parser.add_argument(
        "--actor", required=True, help="Actor performing the action"
    )
    validate_parser.add_argument(
        "--reason", required=True, help="Reason for the manual action"
    )
    validate_parser.add_argument(
        "--bypass-gating", action="store_true", help="Bypass gating flag"
    )
    validate_parser.add_argument(
        "--override-circuit-breaker",
        action="store_true",
        help="Override circuit breaker flag",
    )
    validate_parser.add_argument(
        "--force-deployment", action="store_true", help="Force deployment flag"
    )
    validate_parser.add_argument(
        "--emergency-rollback", action="store_true", help="Emergency rollback flag"
    )

    # Record action command
    record_parser = subparsers.add_parser("record-action", help="Record manual action")
    record_parser.add_argument(
        "--action-type", required=True, help="Type of manual action"
    )
    record_parser.add_argument(
        "--actor", required=True, help="Actor performing the action"
    )
    record_parser.add_argument(
        "--reason", required=True, help="Reason for the manual action"
    )
    record_parser.add_argument(
        "--repository", required=True, help="Repository name (owner/repo)"
    )
    record_parser.add_argument("--workflow-run-id", help="Workflow run ID")
    record_parser.add_argument("--artifact-digest", help="Artifact digest")
    record_parser.add_argument(
        "--bypass-gating", action="store_true", help="Bypass gating flag"
    )
    record_parser.add_argument(
        "--override-circuit-breaker",
        action="store_true",
        help="Override circuit breaker flag",
    )
    record_parser.add_argument(
        "--force-deployment", action="store_true", help="Force deployment flag"
    )
    record_parser.add_argument(
        "--emergency-rollback", action="store_true", help="Emergency rollback flag"
    )

    # Update status command
    update_parser = subparsers.add_parser(
        "update-status", help="Update manual action status"
    )
    update_parser.add_argument("--action-id", required=True, help="Manual action ID")
    update_parser.add_argument(
        "--status",
        required=True,
        choices=["initiated", "in_progress", "completed", "successful", "failed"],
        help="Action status",
    )
    update_parser.add_argument("--outcome", help="Action outcome")
    update_parser.add_argument("--details", help="Additional details")

    # Get status command
    status_parser = subparsers.add_parser("get-status", help="Get manual action status")
    status_parser.add_argument("--action-id", required=True, help="Manual action ID")

    # List recent command
    list_parser = subparsers.add_parser(
        "list-recent", help="List recent manual actions"
    )
    list_parser.add_argument("--repository", help="Repository name (owner/repo)")
    list_parser.add_argument("--action-type", help="Filter by action type")
    list_parser.add_argument(
        "--limit", type=int, default=20, help="Number of actions to show"
    )

    # Generate report command
    report_parser = subparsers.add_parser(
        "generate-report", help="Generate manual actions report"
    )
    report_parser.add_argument("--repository", help="Repository name (owner/repo)")
    report_parser.add_argument(
        "--days", type=int, default=30, help="Days of history to include"
    )

    # Cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Clean up old manual action records"
    )
    cleanup_parser.add_argument(
        "--days", type=int, default=180, help="Days of records to keep"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    manager = ManualActionManager()

    try:
        if args.command == "validate-parameters":
            bypass_flags = {
                "bypass_gating": args.bypass_gating,
                "override_circuit_breaker": args.override_circuit_breaker,
                "force_deployment": args.force_deployment,
                "emergency_rollback": args.emergency_rollback,
            }

            valid, message = manager.validate_manual_action_parameters(
                args.action_type, args.actor, args.reason, bypass_flags
            )
            print(message)
            sys.exit(0 if valid else 1)

        elif args.command == "record-action":
            bypass_flags = {
                "bypass_gating": args.bypass_gating,
                "override_circuit_breaker": args.override_circuit_breaker,
                "force_deployment": args.force_deployment,
                "emergency_rollback": args.emergency_rollback,
            }

            action_id = manager.record_manual_action(
                args.action_type,
                args.actor,
                args.reason,
                args.repository,
                args.workflow_run_id,
                args.artifact_digest,
                bypass_flags,
            )
            print(action_id)

        elif args.command == "update-status":
            manager.update_manual_action_status(
                args.action_id, args.status, args.outcome, args.details
            )

        elif args.command == "get-status":
            status = manager.get_manual_action_status(args.action_id)
            if status:
                print(json.dumps(status, indent=2))
            else:
                print(f"Manual action {args.action_id} not found", file=sys.stderr)
                sys.exit(1)

        elif args.command == "list-recent":
            actions = manager.get_recent_manual_actions(
                args.repository, args.action_type, args.limit
            )
            if actions:
                for action in actions:
                    status_emoji = {
                        "successful": "✅",
                        "completed": "✅",
                        "failed": "❌",
                        "initiated": "🔄",
                        "pending": "⏳",
                    }.get(action.get("status", "unknown"), "❓")

                    bypass_flags = action.get("bypass_flags", {})
                    active_bypasses = [
                        flag for flag, value in bypass_flags.items() if value
                    ]
                    bypass_info = (
                        f" [{', '.join(active_bypasses)}]" if active_bypasses else ""
                    )

                    print(
                        f"{status_emoji} {action['id']} - {action.get('action_type', 'unknown')} - {action.get('actor', 'unknown')} - {action.get('timestamp', 'N/A')}{bypass_info}"
                    )
            else:
                print(f"No manual actions found")

        elif args.command == "generate-report":
            report = manager.generate_manual_actions_report(args.repository, args.days)
            print(report)

        elif args.command == "cleanup":
            removed_count = manager.cleanup_old_manual_actions(args.days)
            if removed_count == 0:
                print("No old records to clean up")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
