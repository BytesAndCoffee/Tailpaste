#!/usr/bin/env python3
"""
Validate GitHub Actions workflow YAML files.
"""

import sys
from pathlib import Path
import yaml


def validate_workflow(filepath):
    """Validate a single workflow file."""
    try:
        with open(filepath, "r") as f:
            workflow = yaml.safe_load(f)

        # Check basic structure
        if "name" not in workflow:
            return False, "Missing 'name' field"

        # 'on' is True when loaded by PyYAML (it's a boolean in YAML)
        # Check for True, 'on', or dict/list
        if not any(key in workflow for key in ["on", True]):
            return False, "Missing 'on' field"

        if "jobs" not in workflow:
            return False, "Missing 'jobs' field"

        # Validate jobs structure
        for job_name, job_config in workflow["jobs"].items():
            # Check if this is a reusable workflow call
            if "uses" in job_config:
                # This job calls another workflow, doesn't need runs-on or steps
                continue

            if "runs-on" not in job_config:
                return False, f"Job '{job_name}' missing 'runs-on'"

            if "steps" not in job_config:
                # Some jobs might not have steps if they have dependencies only
                pass

        return True, "Valid"

    except yaml.YAMLError as e:
        return False, f"YAML error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def main():
    workflows_dir = Path(".github/workflows")

    if not workflows_dir.exists():
        print(f"Error: {workflows_dir} not found")
        sys.exit(1)

    workflow_files = list(workflows_dir.glob("*.yml")) + list(
        workflows_dir.glob("*.yaml")
    )

    if not workflow_files:
        print(f"No workflow files found in {workflows_dir}")
        sys.exit(1)

    print(f"Validating {len(workflow_files)} workflow files...\n")

    all_valid = True
    for workflow_file in sorted(workflow_files):
        valid, message = validate_workflow(workflow_file)
        status = "✅" if valid else "❌"
        print(f"{status} {workflow_file.name}: {message}")

        if not valid:
            all_valid = False

    print()
    if all_valid:
        print("✅ All workflows are valid!")
        sys.exit(0)
    else:
        print("❌ Some workflows have errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
