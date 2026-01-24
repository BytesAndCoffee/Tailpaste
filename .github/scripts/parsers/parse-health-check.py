#!/usr/bin/env python3
"""
Parse health check results from artifact manager JSON
"""
import sys
import json

try:
    data = json.load(sys.stdin)
    hc = data.get('health_check', {})
    print(f"- **Health Check**: {hc.get('status', 'unknown')}")
    if 'timestamp' in hc:
        print(f"- **Health Check Time**: {hc['timestamp']}")
except Exception:
    print("- **Health Check**: unknown")
