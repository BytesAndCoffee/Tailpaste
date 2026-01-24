#!/usr/bin/env python3
"""
Parse functionality test results from artifact manager JSON
"""

import sys
import json

try:
    data = json.load(sys.stdin)
    ft = data.get("functionality_test", {})
    print(f"- **Functionality Test**: {ft.get('status', 'unknown')}")
    if "timestamp" in ft:
        print(f"- **Functionality Test Time**: {ft['timestamp']}")
except Exception:
    print("- **Functionality Test**: unknown")
