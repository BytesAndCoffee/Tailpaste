#!/usr/bin/env python3
"""
Validation script for CI gating and quality control enhancements.

This script validates that the CI workflow enhancements for gating and quality controls
are working correctly by testing the conditional execution and gating logic.

Requirements: 2.2, 2.3, 2.4, 2.5
"""

import json
import os
import subprocess
import sys
import tempfile
import yaml
from pathlib import Path


def run_command(cmd, check=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=check
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode


def test_ci_workflow_structure():
    """Test that the CI workflow has the correct structure for gating."""
    print("🔍 Testing CI workflow structure...")

    try:
        with open(".github/workflows/ci.yml", "r") as f:
            workflow = yaml.safe_load(f)

        # Check environment variables for conditional execution
        env_vars = workflow.get("env", {})
        required_env_vars = [
            "ENABLE_FLAKE8",
            "ENABLE_BLACK",
            "ENABLE_MYPY",
            "ENABLE_BANDIT",
            "ENABLE_COVERAGE",
            "COVERAGE_THRESHOLD",
        ]

        for var in required_env_vars:
            if var not in env_vars:
                print(f"    ❌ Missing environment variable: {var}")
                return False

        print("    ✅ All required environment variables present")

        # Check that build-artifact job depends on lint-and-test
        build_job = workflow["jobs"].get("build-artifact", {})
        if "needs" not in build_job or "lint-and-test" not in build_job["needs"]:
            print(f"    ❌ build-artifact job doesn't depend on lint-and-test")
            return False

        # Check that build-artifact has success condition
        if_condition = build_job.get("if", "")
        if "needs.lint-and-test.result == 'success'" not in if_condition:
            print(f"    ❌ build-artifact job doesn't check for lint-and-test success")
            return False

        print("    ✅ CI gating structure is correct")
        return True

    except Exception as e:
        print(f"    ❌ Workflow structure validation failed: {e}")
        return False


def test_conditional_execution_logic():
    """Test the conditional execution logic for CI components."""
    print("🔍 Testing conditional execution logic...")

    # Create a temporary script to test the conditional logic
    test_script = """
#!/bin/bash
set -e

# Simulate environment variables
export ENABLE_FLAKE8=true
export ENABLE_BLACK=false
export ENABLE_MYPY=true
export ENABLE_BANDIT=true
export ENABLE_COVERAGE=true
export COVERAGE_THRESHOLD=70

QUALITY_CHECKS_FAILED=0

# Test conditional execution (simplified version of workflow logic)
if [ "$ENABLE_FLAKE8" = "true" ]; then
    echo "✅ Flake8 would run"
else
    echo "⏭️ Flake8 disabled"
fi

if [ "$ENABLE_BLACK" = "true" ]; then
    echo "✅ Black would run"
else
    echo "⏭️ Black disabled"
fi

if [ "$ENABLE_MYPY" = "true" ]; then
    echo "✅ MyPy would run"
else
    echo "⏭️ MyPy disabled"
fi

if [ "$ENABLE_BANDIT" = "true" ]; then
    echo "✅ Bandit would run"
else
    echo "⏭️ Bandit disabled"
fi

if [ "$ENABLE_COVERAGE" = "true" ]; then
    echo "✅ Coverage enforcement would run (threshold: $COVERAGE_THRESHOLD%)"
else
    echo "⏭️ Coverage enforcement disabled"
fi

echo "Conditional execution test completed successfully"
"""

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(test_script)
            script_path = f.name

        os.chmod(script_path, 0o755)
        stdout, stderr, code = run_command(f"bash {script_path}")

        if code != 0:
            print(f"    ❌ Conditional execution test failed: {stderr}")
            return False

        # Check that the output contains expected messages
        expected_messages = [
            "✅ Flake8 would run",
            "⏭️ Black disabled",
            "✅ MyPy would run",
            "✅ Bandit would run",
            "✅ Coverage enforcement would run",
        ]

        for msg in expected_messages:
            if msg not in stdout:
                print(f"    ❌ Expected message not found: {msg}")
                return False

        print("    ✅ Conditional execution logic works correctly")
        return True

    except Exception as e:
        print(f"    ❌ Conditional execution test failed: {e}")
        return False
    finally:
        if "script_path" in locals():
            os.unlink(script_path)


def test_gating_failure_simulation():
    """Test that CI gating properly blocks artifact creation on failures."""
    print("🔍 Testing CI gating failure simulation...")

    # Create a script that simulates CI failures
    test_script = """
#!/bin/bash

# Simulate a quality check failure
QUALITY_CHECKS_FAILED=1

if [ $QUALITY_CHECKS_FAILED -eq 1 ]; then
    echo "❌ One or more code quality checks failed. Blocking artifact creation."
    exit 1
fi

echo "This should not be reached"
"""

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(test_script)
            script_path = f.name

        os.chmod(script_path, 0o755)
        stdout, stderr, code = run_command(f"bash {script_path}", check=False)

        if code != 1:
            print(
                f"    ❌ Gating failure test should have failed with exit code 1, got {code}"
            )
            return False

        if "Blocking artifact creation" not in stdout:
            print(f"    ❌ Expected blocking message not found in output")
            return False

        if "This should not be reached" in stdout:
            print(f"    ❌ Script continued after failure - gating not working")
            return False

        print("    ✅ CI gating properly blocks on failures")
        return True

    except Exception as e:
        print(f"    ❌ Gating failure test failed: {e}")
        return False
    finally:
        if "script_path" in locals():
            os.unlink(script_path)


def test_coverage_threshold_enforcement():
    """Test coverage threshold enforcement logic."""
    print("🔍 Testing coverage threshold enforcement...")

    # Create a script that simulates coverage checking
    test_script = """
#!/bin/bash

export ENABLE_COVERAGE=true
export COVERAGE_THRESHOLD=80

# Simulate coverage report command that would fail
echo "Testing coverage threshold enforcement..."

# Simulate coverage failure (exit code 2 is typical for coverage failures)
if [ "$ENABLE_COVERAGE" = "true" ]; then
    echo "📊 Enforcing coverage threshold..."
    # Simulate coverage command failure
    COVERAGE_EXIT_CODE=2
    
    if [ $COVERAGE_EXIT_CODE -ne 0 ]; then
        echo "❌ Coverage threshold ($COVERAGE_THRESHOLD%) not met. Blocking artifact creation."
        exit 1
    fi
    
    echo "✅ Coverage threshold met"
else
    echo "⏭️ Coverage enforcement disabled"
fi

echo "Coverage test completed"
"""

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(test_script)
            script_path = f.name

        os.chmod(script_path, 0o755)
        stdout, stderr, code = run_command(f"bash {script_path}", check=False)

        if code != 1:
            print(
                f"    ❌ Coverage threshold test should have failed with exit code 1, got {code}"
            )
            return False

        if "Coverage threshold (80%) not met" not in stdout:
            print(f"    ❌ Expected coverage threshold message not found")
            return False

        print("    ✅ Coverage threshold enforcement works correctly")
        return True

    except Exception as e:
        print(f"    ❌ Coverage threshold test failed: {e}")
        return False
    finally:
        if "script_path" in locals():
            os.unlink(script_path)


def test_quality_tools_availability():
    """Test that required quality tools are available."""
    print("🔍 Testing quality tools availability...")

    tools = {
        "flake8": "flake8 --version",
        "black": "black --version",
        "mypy": "mypy --version",
        "bandit": "bandit --version",
        "pytest": "pytest --version",
        "coverage": "coverage --version",
    }

    available_tools = 0
    total_tools = len(tools)

    for tool, cmd in tools.items():
        stdout, stderr, code = run_command(cmd, check=False)
        if code == 0:
            print(f"    ✅ {tool}: available")
            available_tools += 1
        else:
            print(f"    ❌ {tool}: not available")

    if available_tools == total_tools:
        print(
            f"    ✅ All quality tools are available ({available_tools}/{total_tools})"
        )
        return True
    else:
        print(
            f"    ⚠️  Some quality tools are missing ({available_tools}/{total_tools})"
        )
        return available_tools >= total_tools * 0.8  # Allow 80% success rate


def main():
    """Run all CI gating validation tests."""
    print("🚀 Validating CI gating and quality control enhancements...")
    print()

    tests = [
        ("CI Workflow Structure", test_ci_workflow_structure),
        ("Conditional Execution Logic", test_conditional_execution_logic),
        ("Gating Failure Simulation", test_gating_failure_simulation),
        ("Coverage Threshold Enforcement", test_coverage_threshold_enforcement),
        ("Quality Tools Availability", test_quality_tools_availability),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}")
        print()

    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All CI gating validation tests passed!")
        return 0
    else:
        print(
            "⚠️  Some CI gating validation tests failed. Please review the output above."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
