#!/usr/bin/env python3
"""
Circuit Breaker Management Script for CI/CD Recovery System

This script provides utilities for managing the circuit breaker state
in the CI/CD recovery system, allowing manual intervention and monitoring.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, Optional


class CircuitBreakerManager:
    def __init__(self, repo: str):
        self.repo = repo
        self.gh_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if not self.gh_token:
            raise ValueError(
                "GitHub token not found. Set GITHUB_TOKEN or GH_TOKEN environment variable."
            )

        # GitHub Actions variables cannot be truly empty; use a lightweight placeholder
        # to represent a cleared value without deleting the variable.
        self.clear_placeholder = "unset"

    def _run_gh_command(self, command: list) -> tuple[bool, str]:
        """Run a GitHub CLI command and return success status and output"""
        try:
            env = os.environ.copy()
            env["GH_TOKEN"] = self.gh_token

            result = subprocess.run(
                ["gh"] + command, capture_output=True, text=True, env=env, timeout=30
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

    def get_variable(self, name: str) -> Optional[str]:
        """Get a GitHub repository variable"""
        success, output = self._run_gh_command(
            ["variable", "get", name, "--repo", self.repo]
        )
        return output if success else None

    def set_variable(self, name: str, value: str) -> bool:
        """Set a GitHub repository variable"""
        success, output = self._run_gh_command(
            ["variable", "set", name, "--body", value, "--repo", self.repo]
        )
        if not success:
            print(f"❌ Failed to set variable {name}: {output}")
        return success

    def get_circuit_breaker_status(self) -> Dict[str, str]:
        """Get comprehensive circuit breaker status"""
        status = {
            "status": self.get_variable("CIRCUIT_BREAKER_STATUS") or "closed",
            "recovery_failure_count": self.get_variable("RECOVERY_FAILURE_COUNT")
            or "0",
            "deployment_failure_count": self.get_variable("DEPLOYMENT_FAILURE_COUNT")
            or "0",
            "recovery_threshold": self.get_variable("CIRCUIT_BREAKER_THRESHOLD") or "3",
            "deployment_threshold": self.get_variable(
                "DEPLOYMENT_CIRCUIT_BREAKER_THRESHOLD"
            )
            or "5",
            "last_recovery_failure_time": self.get_variable(
                "LAST_RECOVERY_FAILURE_TIME"
            )
            or "",
            "last_recovery_failure_reason": self.get_variable(
                "LAST_RECOVERY_FAILURE_REASON"
            )
            or "",
            "last_deployment_failure_time": self.get_variable(
                "LAST_DEPLOYMENT_FAILURE_TIME"
            )
            or "",
            "last_deployment_failure_reason": self.get_variable(
                "LAST_DEPLOYMENT_FAILURE_REASON"
            )
            or "",
            "opened_at": self.get_variable("CIRCUIT_BREAKER_OPENED_AT") or "",
            "opened_by": self.get_variable("CIRCUIT_BREAKER_OPENED_BY") or "",
            "last_trigger": self.get_variable("LAST_CIRCUIT_BREAKER_TRIGGER") or "",
            "trigger_reason": self.get_variable("CIRCUIT_BREAKER_TRIGGER_REASON") or "",
            "last_override": self.get_variable("LAST_CIRCUIT_BREAKER_OVERRIDE") or "",
            "override_by": self.get_variable("CIRCUIT_BREAKER_OVERRIDE_BY") or "",
            "override_reason": self.get_variable("CIRCUIT_BREAKER_OVERRIDE_REASON")
            or "",
        }
        return status

    def print_status(self) -> None:
        """Print current circuit breaker status"""
        status = self.get_circuit_breaker_status()

        print("=" * 60)
        print("🔌 Circuit Breaker Status")
        print("=" * 60)

        # Status with emoji
        cb_status = status["status"]
        if cb_status == "open":
            print(f"Status: 🚫 OPEN")
        elif cb_status == "closed":
            print(f"Status: ✅ CLOSED")
        else:
            print(f"Status: ❓ {cb_status.upper()}")

        print(
            f"Recovery Failures: {status['recovery_failure_count']} / {status['recovery_threshold']}"
        )
        print(
            f"Deployment Failures: {status['deployment_failure_count']} / {status['deployment_threshold']}"
        )

        if status["last_recovery_failure_time"]:
            print(f"Last Recovery Failure: {status['last_recovery_failure_time']}")
            if status["last_recovery_failure_reason"]:
                print(f"  Reason: {status['last_recovery_failure_reason']}")

        if status["last_deployment_failure_time"]:
            print(f"Last Deployment Failure: {status['last_deployment_failure_time']}")
            if status["last_deployment_failure_reason"]:
                print(f"  Reason: {status['last_deployment_failure_reason']}")

        if cb_status == "open":
            if status["opened_at"]:
                print(f"Opened At: {status['opened_at']}")
            if status["opened_by"]:
                print(f"Opened By: {status['opened_by']}")
            if status["trigger_reason"]:
                print(f"Trigger Reason: {status['trigger_reason']}")

        if status["last_override"]:
            print(f"Last Override: {status['last_override']}")
            if status["override_by"]:
                print(f"  By: {status['override_by']}")
            if status["override_reason"]:
                print(f"  Reason: {status['override_reason']}")

        print("=" * 60)

    def open_circuit_breaker(self, reason: str = "manual") -> bool:
        """Manually open the circuit breaker"""
        print("🚫 Opening circuit breaker...")

        timestamp = datetime.now(timezone.utc).isoformat()

        success = all(
            [
                self.set_variable("CIRCUIT_BREAKER_STATUS", "open"),
                self.set_variable("CIRCUIT_BREAKER_OPENED_AT", timestamp),
                self.set_variable("CIRCUIT_BREAKER_OPENED_BY", "manual"),
                self.set_variable("CIRCUIT_BREAKER_TRIGGER_REASON", reason),
                self.set_variable("LAST_CIRCUIT_BREAKER_TRIGGER", timestamp),
            ]
        )

        if success:
            print("✅ Circuit breaker opened successfully")
            # Log the event
            self._log_circuit_breaker_event("opened", reason, "manual")
            return True
        else:
            print("❌ Failed to open circuit breaker")
            return False

    def close_circuit_breaker(self, reset_failures: bool = True) -> bool:
        """Manually close the circuit breaker"""
        print("✅ Closing circuit breaker...")

        variables_to_set = [("CIRCUIT_BREAKER_STATUS", "closed")]

        if reset_failures:
            variables_to_set.extend(
                [
                    ("RECOVERY_FAILURE_COUNT", "0"),
                    ("DEPLOYMENT_FAILURE_COUNT", "0"),
                    ("LAST_RECOVERY_FAILURE_TIME", self.clear_placeholder),
                    ("LAST_RECOVERY_FAILURE_REASON", self.clear_placeholder),
                    ("LAST_DEPLOYMENT_FAILURE_TIME", self.clear_placeholder),
                    ("LAST_DEPLOYMENT_FAILURE_REASON", self.clear_placeholder),
                ]
            )

        # Clear opening-related variables
        variables_to_clear = [
            "CIRCUIT_BREAKER_OPENED_AT",
            "CIRCUIT_BREAKER_OPENED_BY",
            "CIRCUIT_BREAKER_TRIGGER_REASON",
        ]

        success = True

        # Set variables
        for name, value in variables_to_set:
            if not self.set_variable(name, value):
                success = False
                print(f"❌ Failed to set {name}")

        # Clear variables using a placeholder value to satisfy API requirements
        for name in variables_to_clear:
            if not self.set_variable(name, self.clear_placeholder):
                print(f"⚠️  Warning: Failed to clear {name}")

        if success:
            print("✅ Circuit breaker closed successfully")
            if reset_failures:
                print("🔄 Failure counts reset to 0")
            # Log the event
            self._log_circuit_breaker_event("closed", "manual_reset", "manual")
            return True
        else:
            print("❌ Failed to close circuit breaker")
            return False

    def set_threshold(self, threshold: int) -> bool:
        """Set the failure threshold for circuit breaker activation"""
        print(f"🔧 Setting circuit breaker threshold to {threshold}...")

        if threshold < 1:
            print("❌ Threshold must be at least 1")
            return False

        success = self.set_variable("CIRCUIT_BREAKER_THRESHOLD", str(threshold))

        if success:
            print(f"✅ Circuit breaker threshold set to {threshold}")
            return True
        else:
            print("❌ Failed to set threshold")
            return False

    def get_recovery_history(self) -> Dict:
        """Get recent recovery history"""
        history = {
            "last_recovery_trigger": self.get_variable("LAST_RECOVERY_TRIGGER") or "",
            "last_recovery_reason": self.get_variable("LAST_RECOVERY_TRIGGER_REASON")
            or "",
            "last_completed_recovery": self.get_variable("LAST_COMPLETED_RECOVERY")
            or "",
            "last_recovery_session": self.get_variable(
                "LAST_COMPLETED_RECOVERY_SESSION"
            )
            or "",
            "recovery_successful": self.get_variable("RECOVERY_SUCCESSFUL") or "",
            "last_redeployment_trigger": self.get_variable("LAST_REDEPLOYMENT_TRIGGER")
            or "",
            "last_redeployment_artifact": self.get_variable(
                "LAST_REDEPLOYMENT_ARTIFACT"
            )
            or "",
        }
        return history

    def print_recovery_history(self) -> None:
        """Print recent recovery history"""
        history = self.get_recovery_history()

        print("=" * 60)
        print("📋 Recent Recovery History")
        print("=" * 60)

        if history["last_recovery_trigger"]:
            print(f"Last Recovery Trigger: {history['last_recovery_trigger']}")
            if history["last_recovery_reason"]:
                print(f"  Reason: {history['last_recovery_reason']}")

        if history["last_completed_recovery"]:
            print(f"Last Completed Recovery: {history['last_completed_recovery']}")
            if history["last_recovery_session"]:
                print(f"  Session: {history['last_recovery_session']}")
            if history["recovery_successful"]:
                success_status = (
                    "✅ Success"
                    if history["recovery_successful"] == "true"
                    else "❌ Failed"
                )
                print(f"  Result: {success_status}")

        if history["last_redeployment_trigger"]:
            print(f"Last Redeployment: {history['last_redeployment_trigger']}")
            if history["last_redeployment_artifact"]:
                print(f"  Artifact: {history['last_redeployment_artifact']}")

        if not any(history.values()):
            print("No recent recovery history found")

        print("=" * 60)

    def _log_circuit_breaker_event(
        self, action: str, reason: str, triggered_by: str
    ) -> None:
        """Log circuit breaker events for comprehensive tracking"""
        timestamp = datetime.now(timezone.utc).isoformat()

        # Create event log entry
        event_data = {
            "timestamp": timestamp,
            "action": action,
            "reason": reason,
            "triggered_by": triggered_by,
        }

        # Get existing event log
        event_log = self.get_variable("CIRCUIT_BREAKER_EVENT_LOG") or "[]"

        try:
            events = json.loads(event_log)
        except json.JSONDecodeError:
            events = []

        # Add new event
        events.append(event_data)

        # Keep only last 20 events
        events = events[-20:]

        # Store updated log
        self.set_variable("CIRCUIT_BREAKER_EVENT_LOG", json.dumps(events))

        print(f"📝 Circuit breaker event logged: {action} - {reason}")

    def get_event_log(self) -> list:
        """Get circuit breaker event log"""
        event_log = self.get_variable("CIRCUIT_BREAKER_EVENT_LOG") or "[]"

        try:
            return json.loads(event_log)
        except json.JSONDecodeError:
            return []

    def print_event_log(self) -> None:
        """Print circuit breaker event log"""
        events = self.get_event_log()

        print("=" * 60)
        print("📋 Circuit Breaker Event Log")
        print("=" * 60)

        if not events:
            print("No events recorded")
        else:
            for event in events[-10:]:  # Show last 10 events
                timestamp = event.get("timestamp", "unknown")
                action = event.get("action", "unknown")
                reason = event.get("reason", "unknown")
                triggered_by = event.get("triggered_by", "unknown")

                action_emoji = (
                    "🚫" if action == "opened" else "✅" if action == "closed" else "🔄"
                )
                print(f"{action_emoji} {timestamp}")
                print(f"   Action: {action.upper()}")
                print(f"   Reason: {reason}")
                print(f"   Triggered By: {triggered_by}")
                print()

        print("=" * 60)

    def check_thresholds(self) -> Dict[str, bool]:
        """Check if any thresholds are exceeded"""
        status = self.get_circuit_breaker_status()

        recovery_exceeded = int(status["recovery_failure_count"]) >= int(
            status["recovery_threshold"]
        )
        deployment_exceeded = int(status["deployment_failure_count"]) >= int(
            status["deployment_threshold"]
        )

        return {
            "recovery_threshold_exceeded": recovery_exceeded,
            "deployment_threshold_exceeded": deployment_exceeded,
            "any_threshold_exceeded": recovery_exceeded or deployment_exceeded,
        }

    def auto_open_if_needed(self) -> bool:
        """Automatically open circuit breaker if thresholds are exceeded"""
        thresholds = self.check_thresholds()

        if (
            thresholds["any_threshold_exceeded"]
            and self.get_variable("CIRCUIT_BREAKER_STATUS") != "open"
        ):
            reasons = []
            if thresholds["recovery_threshold_exceeded"]:
                reasons.append("recovery_failures")
            if thresholds["deployment_threshold_exceeded"]:
                reasons.append("deployment_failures")

            reason = f"threshold_exceeded: {', '.join(reasons)}"
            return self.open_circuit_breaker(reason)

        return False

    def set_deployment_threshold(self, threshold: int) -> bool:
        """Set the deployment failure threshold for circuit breaker activation"""
        print(f"🔧 Setting deployment circuit breaker threshold to {threshold}...")

        if threshold < 1:
            print("❌ Threshold must be at least 1")
            return False

        success = self.set_variable(
            "DEPLOYMENT_CIRCUIT_BREAKER_THRESHOLD", str(threshold)
        )

        if success:
            print(f"✅ Deployment circuit breaker threshold set to {threshold}")
            return True
        else:
            print("❌ Failed to set deployment threshold")
            return False

    def export_status(self, output_file: str) -> bool:
        """Export circuit breaker status to JSON file"""
        try:
            status = self.get_circuit_breaker_status()
            history = self.get_recovery_history()
            events = self.get_event_log()
            thresholds = self.check_thresholds()

            export_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "circuit_breaker": status,
                "recovery_history": history,
                "event_log": events,
                "threshold_status": thresholds,
            }

            with open(output_file, "w") as f:
                json.dump(export_data, f, indent=2)

            print(f"✅ Status exported to {output_file}")
            return True
        except Exception as e:
            print(f"❌ Failed to export status: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Circuit Breaker Management for CI/CD Recovery System"
    )
    parser.add_argument(
        "--repo", required=True, help="GitHub repository in format owner/repo"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show circuit breaker status")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")
    status_parser.add_argument("--export", help="Export to file")

    # Open command
    open_parser = subparsers.add_parser("open", help="Open circuit breaker")
    open_parser.add_argument("--reason", default="manual", help="Reason for opening")

    # Close command
    close_parser = subparsers.add_parser("close", help="Close circuit breaker")
    close_parser.add_argument(
        "--keep-failures", action="store_true", help="Keep failure counts"
    )

    # Threshold commands
    threshold_parser = subparsers.add_parser(
        "threshold", help="Set recovery failure threshold"
    )
    threshold_parser.add_argument("value", type=int, help="Threshold value")

    deployment_threshold_parser = subparsers.add_parser(
        "deployment-threshold", help="Set deployment failure threshold"
    )
    deployment_threshold_parser.add_argument("value", type=int, help="Threshold value")

    # History command
    history_parser = subparsers.add_parser("history", help="Show recovery history")

    # Event log command
    events_parser = subparsers.add_parser(
        "events", help="Show circuit breaker event log"
    )

    # Check command
    check_parser = subparsers.add_parser(
        "check", help="Check thresholds and auto-open if needed"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        manager = CircuitBreakerManager(args.repo)

        if args.command == "status":
            if args.json:
                status = manager.get_circuit_breaker_status()
                print(json.dumps(status, indent=2))
            else:
                manager.print_status()

            if args.export:
                manager.export_status(args.export)

        elif args.command == "open":
            success = manager.open_circuit_breaker(args.reason)
            return 0 if success else 1

        elif args.command == "close":
            success = manager.close_circuit_breaker(not args.keep_failures)
            return 0 if success else 1

        elif args.command == "threshold":
            success = manager.set_threshold(args.value)
            return 0 if success else 1

        elif args.command == "deployment-threshold":
            success = manager.set_deployment_threshold(args.value)
            return 0 if success else 1

        elif args.command == "history":
            manager.print_recovery_history()

        elif args.command == "events":
            manager.print_event_log()

        elif args.command == "check":
            thresholds = manager.check_thresholds()
            print("🔍 Threshold Check Results:")
            print(
                f"Recovery threshold exceeded: {'✅ Yes' if thresholds['recovery_threshold_exceeded'] else '❌ No'}"
            )
            print(
                f"Deployment threshold exceeded: {'✅ Yes' if thresholds['deployment_threshold_exceeded'] else '❌ No'}"
            )

            if manager.auto_open_if_needed():
                print(
                    "🚫 Circuit breaker automatically opened due to threshold violations"
                )
                return 1
            else:
                print("✅ No action needed - thresholds within limits")
                return 0

        return 0

    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
