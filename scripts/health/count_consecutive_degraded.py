#!/usr/bin/env python3
"""
Count consecutive degraded/unhealthy health checks from history.
"""

import json
import os
import sys


def main():
    try:
        health_history = os.environ.get('HEALTH_HISTORY', '[]')
        
        try:
            history = json.loads(health_history)
        except json.JSONDecodeError:
            print(0)
            return 0
        
        consecutive = 0
        for result in reversed(history):
            if result.get('status') in ['degraded', 'unhealthy']:
                consecutive += 1
            else:
                break
        
        print(consecutive)
        return 0
        
    except Exception:
        print(0)
        return 0


if __name__ == "__main__":
    sys.exit(main())
