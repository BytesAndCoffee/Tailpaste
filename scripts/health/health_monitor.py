#!/usr/bin/env python3
"""
Health monitoring utility for CI/CD system integration
Provides simple interface for health check result recording and failure detection
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional


class HealthMonitor:
    """Health monitoring utility for CI/CD integration"""
    
    def __init__(self, results_dir: str = "/tmp"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def record_health_result(self, session_id: str, status: str, details: Dict[str, Any]) -> bool:
        """Record health check result"""
        try:
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "status": status,
                "details": details
            }
            
            result_file = self.results_dir / f"health_result_{session_id}.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"Health result recorded: {result_file}")
            return True
            
        except Exception as e:
            print(f"Error recording health result: {e}", file=sys.stderr)
            return False
    
    def get_latest_result(self) -> Optional[Dict[str, Any]]:
        """Get the most recent health check result"""
        try:
            result_files = list(self.results_dir.glob("health_result_*.json"))
            if not result_files:
                return None
            
            # Get the most recent file
            latest_file = max(result_files, key=lambda f: f.stat().st_mtime)
            
            with open(latest_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"Error getting latest result: {e}", file=sys.stderr)
            return None
    
    def check_failure_pattern(self, max_history: int = 10) -> Dict[str, Any]:
        """Check for failure patterns in recent health checks"""
        try:
            result_files = list(self.results_dir.glob("health_result_*.json"))
            if not result_files:
                return {"pattern": "no_data", "consecutive_failures": 0}
            
            # Sort by modification time (most recent first)
            result_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Load recent results
            recent_results = []
            for result_file in result_files[:max_history]:
                try:
                    with open(result_file, 'r') as f:
                        result = json.load(f)
                        recent_results.append(result)
                except Exception:
                    continue
            
            if not recent_results:
                return {"pattern": "no_data", "consecutive_failures": 0}
            
            # Count consecutive failures
            consecutive_failures = 0
            consecutive_degraded = 0
            
            for result in recent_results:
                status = result.get("status", "unknown")
                if status == "unhealthy":
                    consecutive_failures += 1
                    consecutive_degraded += 1
                elif status == "degraded":
                    consecutive_degraded += 1
                    break  # Stop counting failures but continue degraded
                else:
                    break  # Stop at first healthy result
            
            # Determine pattern
            pattern = "healthy"
            if consecutive_failures >= 3:
                pattern = "critical_failure"
            elif consecutive_failures >= 1:
                pattern = "failure"
            elif consecutive_degraded >= 3:
                pattern = "persistent_degradation"
            elif consecutive_degraded >= 1:
                pattern = "degradation"
            
            return {
                "pattern": pattern,
                "consecutive_failures": consecutive_failures,
                "consecutive_degraded": consecutive_degraded,
                "total_results": len(recent_results),
                "latest_status": recent_results[0].get("status", "unknown"),
                "latest_timestamp": recent_results[0].get("timestamp", "unknown")
            }
            
        except Exception as e:
            print(f"Error checking failure pattern: {e}", file=sys.stderr)
            return {"pattern": "error", "consecutive_failures": 0}
    
    def should_trigger_recovery(self, failure_pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Determine if recovery should be triggered based on failure pattern"""
        pattern = failure_pattern.get("pattern", "unknown")
        consecutive_failures = failure_pattern.get("consecutive_failures", 0)
        consecutive_degraded = failure_pattern.get("consecutive_degraded", 0)
        
        should_trigger = False
        reason = "no_action_needed"
        urgency = "low"
        
        if pattern == "critical_failure":
            should_trigger = True
            reason = "critical_failure_pattern"
            urgency = "high"
        elif pattern == "failure" and consecutive_failures >= 2:
            should_trigger = True
            reason = "repeated_failures"
            urgency = "medium"
        elif pattern == "persistent_degradation":
            should_trigger = True
            reason = "persistent_degradation"
            urgency = "low"
        
        return {
            "should_trigger": should_trigger,
            "reason": reason,
            "urgency": urgency,
            "pattern_analysis": failure_pattern
        }
    
    def cleanup_old_results(self, max_age_hours: int = 24, max_files: int = 50):
        """Clean up old health check result files"""
        try:
            result_files = list(self.results_dir.glob("health_result_*.json"))
            
            # Remove files older than max_age_hours
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            old_files = [f for f in result_files if f.stat().st_mtime < cutoff_time]
            
            for old_file in old_files:
                old_file.unlink()
                print(f"Removed old result file: {old_file}")
            
            # Keep only the most recent max_files
            remaining_files = [f for f in result_files if f not in old_files]
            if len(remaining_files) > max_files:
                remaining_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                excess_files = remaining_files[max_files:]
                
                for excess_file in excess_files:
                    excess_file.unlink()
                    print(f"Removed excess result file: {excess_file}")
            
            return True
            
        except Exception as e:
            print(f"Error cleaning up old results: {e}", file=sys.stderr)
            return False


def main():
    parser = argparse.ArgumentParser(description="Health monitoring utility for CI/CD integration")
    parser.add_argument("--results-dir", default="/tmp", help="Directory to store health results")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Record command
    record_parser = subparsers.add_parser("record", help="Record health check result")
    record_parser.add_argument("--session-id", required=True, help="Health check session ID")
    record_parser.add_argument("--status", required=True, choices=["healthy", "degraded", "unhealthy"], help="Health status")
    record_parser.add_argument("--details", help="JSON string with additional details")
    
    # Latest command
    latest_parser = subparsers.add_parser("latest", help="Get latest health check result")
    
    # Pattern command
    pattern_parser = subparsers.add_parser("pattern", help="Check failure patterns")
    pattern_parser.add_argument("--max-history", type=int, default=10, help="Maximum number of results to analyze")
    
    # Recovery command
    recovery_parser = subparsers.add_parser("recovery", help="Check if recovery should be triggered")
    recovery_parser.add_argument("--max-history", type=int, default=10, help="Maximum number of results to analyze")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old result files")
    cleanup_parser.add_argument("--max-age-hours", type=int, default=24, help="Maximum age of files to keep")
    cleanup_parser.add_argument("--max-files", type=int, default=50, help="Maximum number of files to keep")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    monitor = HealthMonitor(results_dir=args.results_dir)
    
    if args.command == "record":
        details = {}
        if args.details:
            try:
                details = json.loads(args.details)
            except json.JSONDecodeError as e:
                print(f"Error parsing details JSON: {e}", file=sys.stderr)
                sys.exit(1)
        
        success = monitor.record_health_result(args.session_id, args.status, details)
        sys.exit(0 if success else 1)
    
    elif args.command == "latest":
        result = monitor.get_latest_result()
        if result:
            print(json.dumps(result, indent=2))
        else:
            print("No health check results found")
            sys.exit(1)
    
    elif args.command == "pattern":
        pattern = monitor.check_failure_pattern(max_history=args.max_history)
        print(json.dumps(pattern, indent=2))
    
    elif args.command == "recovery":
        pattern = monitor.check_failure_pattern(max_history=args.max_history)
        recovery_decision = monitor.should_trigger_recovery(pattern)
        print(json.dumps(recovery_decision, indent=2))
        
        # Exit with code 2 if recovery should be triggered
        if recovery_decision.get("should_trigger", False):
            sys.exit(2)
    
    elif args.command == "cleanup":
        success = monitor.cleanup_old_results(
            max_age_hours=args.max_age_hours,
            max_files=args.max_files
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()