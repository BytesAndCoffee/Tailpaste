#!/usr/bin/env python3
"""
Parse deployment verification results from artifact manager JSON
"""

import sys
import json

try:
    data = json.load(sys.stdin)
    dv = data.get("deployment_verification", {})
    print(f"- **Deployment Verification**: {dv.get('status', 'unknown')}")
    if "timestamp" in dv:
        print(f"- **Verification Time**: {dv['timestamp']}")
except Exception:
    print("- **Deployment Verification**: unknown")
