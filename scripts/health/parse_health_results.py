#!/usr/bin/env python3
"""
Parse health results JSON file and extract specific fields.
"""

import json
import sys


def main():
    if len(sys.argv) != 3:
        print("Usage: parse_health_results.py <json_file> <field>", file=sys.stderr)
        sys.exit(1)

    json_file = sys.argv[1]
    field = sys.argv[2]

    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        if field == "overall_status":
            print(data.get("overall_status", "unknown"))
        elif field == "health_details":
            print(data.get("health_details", "Health check completed"))
        elif field == "service_available":
            status = data.get("checks", {}).get("service", {}).get("status")
            print(str(status == "passed").lower())
        elif field == "functionality_ok":
            status = data.get("checks", {}).get("functionality", {}).get("status")
            print(str(status == "passed").lower())
        elif field == "container_healthy":
            status = data.get("checks", {}).get("container", {}).get("status")
            print(str(status == "passed").lower())
        else:
            print(f"Unknown field: {field}", file=sys.stderr)
            sys.exit(1)

    except FileNotFoundError:
        print(f"File not found: {json_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
