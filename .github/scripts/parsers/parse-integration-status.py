#!/usr/bin/env python3
"""
Parse integration test status from artifact manager JSON
"""

import sys
import json

try:
    data = json.load(sys.stdin)
    print(data.get("integration", {}).get("status", "unknown"))
except Exception:
    print("unknown")
