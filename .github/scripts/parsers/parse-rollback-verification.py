#!/usr/bin/env python3
"""
Parse rollback verification results from artifact manager JSON
"""

import sys
import json

try:
    data = json.load(sys.stdin)
    rv = data.get("rollback_verification", {})
    print(f"- **Rollback Verification**: {rv.get('status', 'unknown')}")
    if "timestamp" in rv:
        print(f"- **Verification Time**: {rv['timestamp']}")
except Exception:
    print("- **Rollback Verification**: unknown")
