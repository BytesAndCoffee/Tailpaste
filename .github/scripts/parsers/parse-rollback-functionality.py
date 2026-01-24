#!/usr/bin/env python3
"""
Parse rollback functionality test results from artifact manager JSON
"""
import sys
import json

try:
    data = json.load(sys.stdin)
    rft = data.get('rollback_functionality_test', {})
    print(f"- **Rollback Functionality Test**: {rft.get('status', 'unknown')}")
    if 'timestamp' in rft:
        print(f"- **Functionality Test Time**: {rft['timestamp']}")
except Exception:
    print("- **Rollback Functionality Test**: unknown")
