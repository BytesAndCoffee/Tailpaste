#!/usr/bin/env python3
"""
Validation script for artifact workflow enhancements.

This script validates that the CI workflow enhancements for artifact management
are working correctly by testing the artifact manager functionality.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1
"""

import json
import os
import subprocess
import sys
import tempfile
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


def test_artifact_manager():
    """Test the artifact manager functionality."""
    print("🔍 Testing artifact manager functionality...")

    # Test digest validation
    print("  Testing digest validation...")
    valid_digest = (
        "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    )
    invalid_digest = "invalid-digest"

    stdout, stderr, code = run_command(
        f"python scripts/artifact_manager.py validate-digest --digest {valid_digest} --registry ghcr.io --repository test/repo",
        check=False,
    )
    if (
        code != 1
    ):  # Should fail because artifact doesn't exist, but digest format is valid
        print(
            f"    ❌ Digest validation test failed: expected failure due to non-existent artifact"
        )
        return False

    # Test invalid digest format
    stdout, stderr, code = run_command(
        f"python scripts/artifact_manager.py validate-digest --digest {invalid_digest} --registry ghcr.io --repository test/repo",
        check=False,
    )
    if code != 1:
        print(f"    ❌ Invalid digest format test failed")
        return False

    print("    ✅ Digest validation tests passed")

    # Test artifact recording and retrieval
    print("  Testing artifact recording...")
    test_commit = "abc123def456"
    test_registry = "ghcr.io"
    test_repo = "test/repository"

    # Record an artifact
    stdout, stderr, code = run_command(
        f"python scripts/artifact_manager.py record-artifact --digest {valid_digest} --commit {test_commit} --registry {test_registry} --repository {test_repo}"
    )
    if code != 0:
        print(f"    ❌ Artifact recording failed: {stderr}")
        return False

    # Check if artifact exists
    stdout, stderr, code = run_command(
        f"python scripts/artifact_manager.py check-existing --registry {test_registry} --repository {test_repo} --commit {test_commit}"
    )
    if code != 0:
        print(f"    ❌ Artifact existence check failed: {stderr}")
        return False

    # Get digest for commit
    stdout, stderr, code = run_command(
        f"python scripts/artifact_manager.py get-digest --commit {test_commit}"
    )
    if code != 0 or stdout != valid_digest:
        print(f"    ❌ Get digest failed: expected {valid_digest}, got {stdout}")
        return False

    print("    ✅ Artifact recording and retrieval tests passed")

    # Clean up test artifacts file
    artifacts_file = Path(".artifacts.json")
    if artifacts_file.exists():
        artifacts_file.unlink()

    return True


def test_workflow_syntax():
    """Test that the CI workflow has valid YAML syntax."""
    print("🔍 Testing CI workflow syntax...")

    try:
        import yaml

        with open(".github/workflows/ci.yml", "r") as f:
            workflow = yaml.safe_load(f)

        # Check required sections exist
        required_sections = ["name", "jobs"]
        for section in required_sections:
            if section not in workflow:
                print(f"    ❌ Missing required section: {section}")
                return False

        # Check that 'on' section exists (might be parsed as True)
        if True not in workflow and "on" not in workflow:
            print(f"    ❌ Missing 'on' trigger section")
            return False

        # Check that build-artifact job exists
        if "build-artifact" not in workflow["jobs"]:
            print(f"    ❌ Missing build-artifact job")
            return False

        # Check that environment variables are set
        if "env" not in workflow or "REGISTRY" not in workflow["env"]:
            print(f"    ❌ Missing REGISTRY environment variable")
            return False

        print("    ✅ CI workflow syntax is valid")
        return True

    except ImportError:
        print("    ⚠️  PyYAML not available, skipping YAML syntax validation")
        return True
    except Exception as e:
        print(f"    ❌ Workflow syntax validation failed: {e}")
        return False


def test_docker_buildx_availability():
    """Test that Docker Buildx is available for multi-platform builds."""
    print("🔍 Testing Docker Buildx availability...")

    stdout, stderr, code = run_command("docker buildx version", check=False)
    if code != 0:
        print(f"    ⚠️  Docker Buildx not available: {stderr}")
        return True  # Not critical for basic functionality

    print(f"    ✅ Docker Buildx available: {stdout.split()[0]}")
    return True


def test_github_actions_integration():
    """Test GitHub Actions specific functionality."""
    print("🔍 Testing GitHub Actions integration...")

    # Check if we're in a GitHub Actions environment
    if "GITHUB_ACTIONS" in os.environ:
        print("    ✅ Running in GitHub Actions environment")

        # Check required environment variables
        required_vars = ["GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_REF"]
        for var in required_vars:
            if var not in os.environ:
                print(f"    ❌ Missing required environment variable: {var}")
                return False

        print("    ✅ GitHub Actions environment variables present")
    else:
        print("    ℹ️  Not running in GitHub Actions environment (local testing)")

    return True


def main():
    """Run all validation tests."""
    print("🚀 Validating CI/CD artifact workflow enhancements...")
    print()

    tests = [
        ("Artifact Manager Functionality", test_artifact_manager),
        ("Workflow Syntax", test_workflow_syntax),
        ("Docker Buildx Availability", test_docker_buildx_availability),
        ("GitHub Actions Integration", test_github_actions_integration),
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
        print("🎉 All validation tests passed!")
        return 0
    else:
        print("⚠️  Some validation tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
