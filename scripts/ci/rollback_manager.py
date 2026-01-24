#!/usr/bin/env python3
"""
Rollback Manager - Utility for managing rollback operations in CI/CD pipeline.

This script provides functionality for:
- Validating rollback prerequisites
- Managing rollback state and tracking
- Querying rollback history and status
- Supporting rollback verification

Requirements: 10.1, 10.2, 10.4, 10.5
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class RollbackManager:
    """Manages rollback operations and state tracking."""

    def __init__(self):
        self.rollback_history_file = Path(".rollback_history.json")

    def load_rollback_history(self) -> Dict:
        """Load rollback history from file."""
        if self.rollback_history_file.exists():
            try:
                with open(self.rollback_history_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(
                    f"Warning: Could not load rollback history file: {e}",
                    file=sys.stderr,
                )
        return {"rollbacks": [], "metadata": {"version": "1.0"}}

    def save_rollback_history(self, data: Dict) -> None:
        """Save rollback history to file."""
        try:
            with open(self.rollback_history_file, "w") as f:
                json.dump(data, f, indent=2, sort_keys=True)
        except IOError as e:
            print(f"Error: Could not save rollback history file: {e}", file=sys.stderr)
            sys.exit(1)

    def validate_rollback_prerequisites(self, repository: str) -> Tuple[bool, str]:
        """Validate that rollback prerequisites are met."""
        try:
            # Check if backup artifact digest is available
            result = subprocess.run(
                [
                    "gh",
                    "variable",
                    "get",
                    "BACKUP_ARTIFACT_DIGEST",
                    "--repo",
                    repository,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return (
                    False,
                    "No backup artifact digest found - cannot perform digest-based rollback",
                )

            backup_digest = result.stdout.strip()
            if not backup_digest:
                return False, "Backup artifact digest is empty"

            # Validate digest format
            if not self._validate_digest_format(backup_digest):
                return False, f"Invalid backup digest format: {backup_digest}"

            # Check if backup timestamp is available
            result = subprocess.run(
                ["gh", "variable", "get", "BACKUP_CREATED_AT", "--repo", repository],
                capture_output=True,
                text=True,
                timeout=30,
            )

            backup_timestamp = result.stdout.strip() if result.returncode == 0 else ""

            # Check current deployment state
            result = subprocess.run(
                [
                    "gh",
                    "variable",
                    "get",
                    "DEPLOYED_ARTIFACT_DIGEST",
                    "--repo",
                    repository,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            current_digest = result.stdout.strip() if result.returncode == 0 else ""

            if current_digest == backup_digest:
                return (
                    False,
                    "Current deployment already matches backup artifact - no rollback needed",
                )

            return (
                True,
                f"Rollback prerequisites validated - can rollback to {backup_digest}",
            )

        except subprocess.TimeoutExpired:
            return False, "Timeout while checking rollback prerequisites"
        except subprocess.SubprocessError as e:
            return False, f"Error checking rollback prerequisites: {e}"

    def _validate_digest_format(self, digest: str) -> bool:
        """Validate that a digest follows the expected SHA256 format."""
        import re

        if not digest:
            return False
        # Docker digest format: sha256:64-character-hex-string
        pattern = r"^sha256:[a-f0-9]{64}$"
        return bool(re.match(pattern, digest))

    def record_rollback_attempt(
        self,
        repository: str,
        target_digest: str,
        method: str,
        initiated_by: str,
        reason: str = None,
    ) -> str:
        """Record a rollback attempt in history."""
        data = self.load_rollback_history()

        rollback_id = f"rollback-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        rollback_record = {
            "id": rollback_id,
            "repository": repository,
            "target_digest": target_digest,
            "method": method,
            "initiated_by": initiated_by,
            "initiated_at": datetime.utcnow().isoformat() + "Z",
            "reason": reason,
            "status": "initiated",
            "stages": {
                "preparation": {"status": "pending", "timestamp": None},
                "execution": {"status": "pending", "timestamp": None},
                "verification": {"status": "pending", "timestamp": None},
                "health_check": {"status": "pending", "timestamp": None},
            },
        }

        data["rollbacks"].append(rollback_record)
        data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"

        self.save_rollback_history(data)
        print(f"Recorded rollback attempt: {rollback_id}")
        return rollback_id

    def update_rollback_stage(
        self, rollback_id: str, stage: str, status: str, details: str = None
    ) -> None:
        """Update the status of a rollback stage."""
        data = self.load_rollback_history()

        # Find rollback record
        rollback_found = False
        for rollback in data["rollbacks"]:
            if rollback["id"] == rollback_id:
                if stage in rollback["stages"]:
                    rollback["stages"][stage] = {
                        "status": status,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "details": details,
                    }

                    # Update overall rollback status based on stage
                    if status == "failed":
                        rollback["status"] = "failed"
                        rollback["failure_stage"] = stage
                        rollback["failure_reason"] = details
                    elif status == "completed" and stage == "health_check":
                        rollback["status"] = "successful"
                        rollback["completed_at"] = datetime.utcnow().isoformat() + "Z"

                    rollback_found = True
                    print(f"Updated rollback {rollback_id} stage {stage} to: {status}")
                    break
                else:
                    print(
                        f"Warning: Unknown stage {stage} for rollback {rollback_id}",
                        file=sys.stderr,
                    )
                    return

        if not rollback_found:
            print(f"Warning: Rollback {rollback_id} not found", file=sys.stderr)
            return

        data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
        self.save_rollback_history(data)

    def get_rollback_status(self, rollback_id: str) -> Optional[Dict]:
        """Get the status of a specific rollback."""
        data = self.load_rollback_history()

        for rollback in data["rollbacks"]:
            if rollback["id"] == rollback_id:
                return rollback

        return None

    def get_recent_rollbacks(self, repository: str, limit: int = 10) -> List[Dict]:
        """Get recent rollbacks for a repository."""
        data = self.load_rollback_history()

        # Filter by repository and sort by initiated_at (most recent first)
        repo_rollbacks = [
            rb for rb in data["rollbacks"] if rb.get("repository") == repository
        ]

        repo_rollbacks.sort(key=lambda x: x.get("initiated_at", ""), reverse=True)

        return repo_rollbacks[:limit]

    def validate_rollback_target(
        self, target_digest: str, registry: str, repository: str
    ) -> Tuple[bool, str]:
        """Validate that the rollback target is valid and accessible."""
        if not self._validate_digest_format(target_digest):
            return False, f"Invalid digest format: {target_digest}"

        try:
            # Use docker manifest inspect to check if the image exists
            cmd = [
                "docker",
                "manifest",
                "inspect",
                f"{registry}/{repository}@{target_digest}",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return True, f"Rollback target validated: {target_digest}"
            else:
                return False, f"Rollback target not found in registry: {target_digest}"

        except subprocess.TimeoutExpired:
            return False, "Timeout while validating rollback target"
        except subprocess.SubprocessError as e:
            return False, f"Error validating rollback target: {e}"

    def generate_rollback_report(self, repository: str) -> str:
        """Generate a comprehensive rollback report for a repository."""
        recent_rollbacks = self.get_recent_rollbacks(repository, 20)

        if not recent_rollbacks:
            return f"No rollback history found for repository: {repository}"

        report_lines = [
            f"# Rollback Report for {repository}",
            f"Generated at: {datetime.utcnow().isoformat()}Z",
            "",
            f"Total rollbacks: {len(recent_rollbacks)}",
            "",
        ]

        # Summary statistics
        successful_count = len(
            [rb for rb in recent_rollbacks if rb.get("status") == "successful"]
        )
        failed_count = len(
            [rb for rb in recent_rollbacks if rb.get("status") == "failed"]
        )
        pending_count = len(
            [
                rb
                for rb in recent_rollbacks
                if rb.get("status") not in ["successful", "failed"]
            ]
        )

        report_lines.extend(
            [
                "## Summary Statistics",
                f"- Successful: {successful_count}",
                f"- Failed: {failed_count}",
                f"- Pending/In Progress: {pending_count}",
                "",
            ]
        )

        # Recent rollbacks
        report_lines.extend(["## Recent Rollbacks", ""])

        for rollback in recent_rollbacks[:10]:  # Show last 10
            status_emoji = {
                "successful": "✅",
                "failed": "❌",
                "initiated": "🔄",
                "pending": "⏳",
            }.get(rollback.get("status", "unknown"), "❓")

            report_lines.extend(
                [
                    f"### {status_emoji} {rollback['id']}",
                    f"- **Status**: {rollback.get('status', 'unknown')}",
                    f"- **Target**: `{rollback.get('target_digest', 'N/A')}`",
                    f"- **Method**: {rollback.get('method', 'unknown')}",
                    f"- **Initiated By**: {rollback.get('initiated_by', 'unknown')}",
                    f"- **Initiated At**: {rollback.get('initiated_at', 'N/A')}",
                ]
            )

            if rollback.get("completed_at"):
                report_lines.append(f"- **Completed At**: {rollback['completed_at']}")

            if rollback.get("failure_reason"):
                report_lines.extend(
                    [
                        f"- **Failure Stage**: {rollback.get('failure_stage', 'unknown')}",
                        f"- **Failure Reason**: {rollback.get('failure_reason', 'unknown')}",
                    ]
                )

            if rollback.get("reason"):
                report_lines.append(f"- **Reason**: {rollback['reason']}")

            report_lines.append("")

        return "\n".join(report_lines)

    def cleanup_old_rollback_records(self, days_to_keep: int = 90) -> int:
        """Clean up old rollback records to prevent file bloat."""
        from datetime import datetime, timedelta

        data = self.load_rollback_history()
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        original_count = len(data["rollbacks"])

        # Keep rollbacks newer than cutoff date
        data["rollbacks"] = [
            rb
            for rb in data["rollbacks"]
            if datetime.fromisoformat(rb.get("initiated_at", "").replace("Z", "+00:00"))
            > cutoff_date
        ]

        removed_count = original_count - len(data["rollbacks"])

        if removed_count > 0:
            data["metadata"]["last_cleanup"] = datetime.utcnow().isoformat() + "Z"
            data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
            self.save_rollback_history(data)
            print(f"Cleaned up {removed_count} old rollback records")

        return removed_count


def main():
    """Main CLI interface for rollback management."""
    parser = argparse.ArgumentParser(
        description="Manage rollback operations and tracking"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate prerequisites command
    validate_parser = subparsers.add_parser(
        "validate-prerequisites", help="Validate rollback prerequisites"
    )
    validate_parser.add_argument(
        "--repository", required=True, help="Repository name (owner/repo)"
    )

    # Record rollback attempt command
    record_parser = subparsers.add_parser(
        "record-attempt", help="Record rollback attempt"
    )
    record_parser.add_argument(
        "--repository", required=True, help="Repository name (owner/repo)"
    )
    record_parser.add_argument(
        "--target-digest", required=True, help="Target artifact digest"
    )
    record_parser.add_argument(
        "--method",
        required=True,
        choices=["digest-based", "file-based"],
        help="Rollback method",
    )
    record_parser.add_argument(
        "--initiated-by", required=True, help="Who initiated the rollback"
    )
    record_parser.add_argument("--reason", help="Reason for rollback")

    # Update stage command
    update_parser = subparsers.add_parser(
        "update-stage", help="Update rollback stage status"
    )
    update_parser.add_argument("--rollback-id", required=True, help="Rollback ID")
    update_parser.add_argument(
        "--stage",
        required=True,
        choices=["preparation", "execution", "verification", "health_check"],
        help="Rollback stage",
    )
    update_parser.add_argument(
        "--status",
        required=True,
        choices=["pending", "in_progress", "completed", "failed"],
        help="Stage status",
    )
    update_parser.add_argument("--details", help="Additional details")

    # Get status command
    status_parser = subparsers.add_parser("get-status", help="Get rollback status")
    status_parser.add_argument("--rollback-id", required=True, help="Rollback ID")

    # List recent command
    list_parser = subparsers.add_parser("list-recent", help="List recent rollbacks")
    list_parser.add_argument(
        "--repository", required=True, help="Repository name (owner/repo)"
    )
    list_parser.add_argument(
        "--limit", type=int, default=10, help="Number of rollbacks to show"
    )

    # Validate target command
    validate_target_parser = subparsers.add_parser(
        "validate-target", help="Validate rollback target"
    )
    validate_target_parser.add_argument(
        "--target-digest", required=True, help="Target artifact digest"
    )
    validate_target_parser.add_argument(
        "--registry", required=True, help="Container registry URL"
    )
    validate_target_parser.add_argument(
        "--repository", required=True, help="Repository name"
    )

    # Generate report command
    report_parser = subparsers.add_parser(
        "generate-report", help="Generate rollback report"
    )
    report_parser.add_argument(
        "--repository", required=True, help="Repository name (owner/repo)"
    )

    # Cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Clean up old rollback records"
    )
    cleanup_parser.add_argument(
        "--days", type=int, default=90, help="Days of records to keep"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    manager = RollbackManager()

    try:
        if args.command == "validate-prerequisites":
            valid, message = manager.validate_rollback_prerequisites(args.repository)
            print(message)
            sys.exit(0 if valid else 1)

        elif args.command == "record-attempt":
            rollback_id = manager.record_rollback_attempt(
                args.repository,
                args.target_digest,
                args.method,
                args.initiated_by,
                args.reason,
            )
            print(rollback_id)

        elif args.command == "update-stage":
            manager.update_rollback_stage(
                args.rollback_id, args.stage, args.status, args.details
            )

        elif args.command == "get-status":
            status = manager.get_rollback_status(args.rollback_id)
            if status:
                print(json.dumps(status, indent=2))
            else:
                print(f"Rollback {args.rollback_id} not found", file=sys.stderr)
                sys.exit(1)

        elif args.command == "list-recent":
            rollbacks = manager.get_recent_rollbacks(args.repository, args.limit)
            if rollbacks:
                for rb in rollbacks:
                    status_emoji = {
                        "successful": "✅",
                        "failed": "❌",
                        "initiated": "🔄",
                        "pending": "⏳",
                    }.get(rb.get("status", "unknown"), "❓")

                    print(
                        f"{status_emoji} {rb['id']} - {rb.get('status', 'unknown')} - {rb.get('initiated_at', 'N/A')}"
                    )
            else:
                print(f"No rollbacks found for {args.repository}")

        elif args.command == "validate-target":
            valid, message = manager.validate_rollback_target(
                args.target_digest, args.registry, args.repository
            )
            print(message)
            sys.exit(0 if valid else 1)

        elif args.command == "generate-report":
            report = manager.generate_rollback_report(args.repository)
            print(report)

        elif args.command == "cleanup":
            removed_count = manager.cleanup_old_rollback_records(args.days)
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
