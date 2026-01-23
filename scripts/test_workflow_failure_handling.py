#!/usr/bin/env python3
"""
Test script to simulate health check failures for workflow testing.

This script can be used to test the health check workflow's failure handling
by simulating various failure scenarios.
"""

import argparse
import json
import sys
from pathlib import Path


def simulate_failure(failure_type: str, export_path: str = None):
    """Simulate different types of health check failures."""
    
    failure_scenarios = {
        "service": {
            "description": "Service unavailable - simulates network error",
            "exit_code": 1,
            "results": {
                "timestamp": "2026-01-23T19:36:34Z",
                "checks": {
                    "service": False,
                    "database": True,
                    "tailscale": True,
                    "logs": True,
                },
                "errors": ["Service unavailable: Connection refused"],
                "warnings": [],
                "overall_status": "unhealthy",
            },
        },
        "database": {
            "description": "Database integrity failure",
            "exit_code": 1,
            "results": {
                "timestamp": "2026-01-23T19:36:34Z",
                "checks": {
                    "service": True,
                    "database": False,
                    "tailscale": True,
                    "logs": True,
                },
                "errors": ["Database integrity check failed: corruption detected"],
                "warnings": [],
                "overall_status": "unhealthy",
            },
        },
        "multiple": {
            "description": "Multiple check failures",
            "exit_code": 1,
            "results": {
                "timestamp": "2026-01-23T19:36:34Z",
                "checks": {
                    "service": False,
                    "database": False,
                    "tailscale": False,
                    "logs": True,
                },
                "errors": [
                    "Service unavailable: Connection refused",
                    "Database error: timeout",
                    "Tailscale is not connected",
                ],
                "warnings": [],
                "overall_status": "unhealthy",
            },
        },
        "timeout": {
            "description": "Service timeout - slow response",
            "exit_code": 1,
            "results": {
                "timestamp": "2026-01-23T19:36:34Z",
                "checks": {
                    "service": False,
                    "database": True,
                    "tailscale": True,
                    "logs": True,
                },
                "errors": ["Health check error: Request timeout after 10s"],
                "warnings": [],
                "overall_status": "unhealthy",
            },
        },
    }
    
    if failure_type not in failure_scenarios:
        print(f"❌ Unknown failure type: {failure_type}")
        print(f"Available types: {', '.join(failure_scenarios.keys())}")
        return 2
    
    scenario = failure_scenarios[failure_type]
    
    print("=" * 60)
    print(f"🧪 Simulating Health Check Failure: {failure_type}")
    print(f"📝 Description: {scenario['description']}")
    print("=" * 60)
    print()
    
    # Print failure details
    print("❌ Health check failed!")
    for error in scenario["results"]["errors"]:
        print(f"  - {error}")
    
    print()
    print(f"Exit code: {scenario['exit_code']}")
    
    # Export results if requested
    if export_path:
        Path(export_path).parent.mkdir(parents=True, exist_ok=True)
        with open(export_path, "w") as f:
            json.dump(scenario["results"], f, indent=2)
        print(f"\n📄 Results exported to: {export_path}")
    
    return scenario["exit_code"]


def main():
    parser = argparse.ArgumentParser(
        description="Simulate health check failures for workflow testing"
    )
    parser.add_argument(
        "failure_type",
        choices=["service", "database", "multiple", "timeout"],
        help="Type of failure to simulate",
    )
    parser.add_argument(
        "--export",
        help="Export results to JSON file",
        default=None,
    )
    
    args = parser.parse_args()
    
    exit_code = simulate_failure(args.failure_type, args.export)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
