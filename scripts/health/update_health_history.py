#!/usr/bin/env python3
"""
Update health check history by adding a new result and keeping only the last 10 entries.
"""

import json
import os
import sys


def main():
    try:
        # Get input from environment variables
        health_history = os.environ.get('HEALTH_HISTORY', '[]')
        timestamp = os.environ.get('TIMESTAMP', '')
        overall_health = os.environ.get('OVERALL_HEALTH', '')
        monitoring_session_id = os.environ.get('MONITORING_SESSION_ID', '')
        
        # Parse existing history
        try:
            history = json.loads(health_history)
        except json.JSONDecodeError:
            history = []
        
        # Add new result
        new_result = {
            'timestamp': timestamp,
            'status': overall_health,
            'session_id': monitoring_session_id
        }
        
        history.append(new_result)
        
        # Keep only last 10 results
        history = history[-10:]
        
        # Output as compact JSON
        print(json.dumps(history, separators=(',', ':')))
        return 0
        
    except Exception as e:
        print(f"Error updating health history: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
