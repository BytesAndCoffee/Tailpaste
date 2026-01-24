#!/usr/bin/env python3
"""
Parse rollback health check results from artifact manager JSON
"""

import sys
import json

try:
    data = json.load(sys.stdin)
    rhc = data.get("rollback_health_check", {})
    print(f"- **Rollback Health Check**: {rhc.get('status', 'unknown')}")
    if "timestamp" in rhc:
        print(f"- **Health Check Time**: {rhc['timestamp']}")
except Exception:
    print("- **Rollback Health Check**: unknown")
