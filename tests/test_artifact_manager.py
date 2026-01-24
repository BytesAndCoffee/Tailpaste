"""
Tests for the artifact manager functionality.

These tests validate the artifact management utilities used in the CI/CD pipeline.
Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the artifact manager - must be after sys.path modification
sys.path.append("scripts/ci")
from artifact_manager import ArtifactManager  # noqa: E402


class TestArtifactManager(unittest.TestCase):
    """Test cases for ArtifactManager class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        self.manager = ArtifactManager()

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_validate_digest_valid_format(self):
        """Test that valid digest formats are accepted."""
        valid_digest = (
            "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        self.assertTrue(self.manager.validate_digest(valid_digest))

    def test_validate_digest_invalid_format(self):
        """Test that invalid digest formats are rejected."""
        invalid_digests = [
            "invalid-digest",
            "sha256:short",
            "md5:1234567890abcdef1234567890abcdef",
            "",
            None,
            "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdefg",  # invalid char
        ]

        for digest in invalid_digests:
            with self.subTest(digest=digest):
                self.assertFalse(self.manager.validate_digest(digest))

    def test_record_and_retrieve_artifact(self):
        """Test recording and retrieving artifact metadata."""
        digest = (
            "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        commit = "abc123def456"
        registry = "ghcr.io"
        repository = "test/repo"

        # Record artifact
        self.manager.record_artifact(digest, commit, registry, repository)

        # Check if artifact exists
        existing_digest = self.manager.check_existing_artifact(
            registry, repository, commit
        )
        self.assertEqual(existing_digest, digest)

        # Get digest for commit
        retrieved_digest = self.manager.get_digest_for_commit(commit)
        self.assertEqual(retrieved_digest, digest)

    def test_check_existing_artifact_not_found(self):
        """Test checking for non-existent artifact."""
        result = self.manager.check_existing_artifact(
            "ghcr.io", "test/repo", "nonexistent"
        )
        self.assertIsNone(result)

    def test_load_save_artifacts(self):
        """Test loading and saving artifact metadata."""
        # Test with empty file
        data = self.manager.load_artifacts()
        expected_structure = {"artifacts": {}, "metadata": {"version": "1.0"}}
        self.assertEqual(data, expected_structure)

        # Add some data and save
        data["artifacts"]["test"] = {"digest": "sha256:test", "commit": "test123"}
        self.manager.save_artifacts(data)

        # Load again and verify
        loaded_data = self.manager.load_artifacts()
        self.assertEqual(loaded_data["artifacts"]["test"]["digest"], "sha256:test")

    def test_record_artifact_invalid_digest(self):
        """Test that recording with invalid digest raises error."""
        with self.assertRaises(SystemExit):
            self.manager.record_artifact("invalid-digest", "commit", "registry", "repo")

    @patch("subprocess.run")
    def test_validate_artifact_exists_success(self, mock_run):
        """Test successful artifact validation."""
        mock_run.return_value = MagicMock(returncode=0)

        digest = (
            "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        result = self.manager.validate_artifact_exists(digest, "ghcr.io", "test/repo")

        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_validate_artifact_exists_failure(self, mock_run):
        """Test failed artifact validation."""
        mock_run.return_value = MagicMock(returncode=1)

        digest = (
            "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        result = self.manager.validate_artifact_exists(digest, "ghcr.io", "test/repo")

        self.assertFalse(result)

    def test_generate_content_hash(self):
        """Test content hash generation."""
        # Create a test file
        test_file = Path("test_file.txt")
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        # Generate hash
        content_hash = self.manager.generate_content_hash(str(test_file))

        # Verify format
        self.assertTrue(content_hash.startswith("sha256:"))
        self.assertEqual(len(content_hash), 71)  # sha256: + 64 hex chars

        # Verify consistency
        content_hash2 = self.manager.generate_content_hash(str(test_file))
        self.assertEqual(content_hash, content_hash2)

    def test_update_artifact_status(self):
        """Test updating artifact status."""
        digest = (
            "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        commit = "abc123def456"
        registry = "ghcr.io"
        repository = "test/repo"

        # Record artifact first
        self.manager.record_artifact(digest, commit, registry, repository)

        # Update status
        self.manager.update_artifact_status(digest, "testing", "2024-01-23T10:00:00Z")

        # Verify status
        status = self.manager.get_artifact_status(digest)
        self.assertEqual(status, "testing")

    def test_get_artifact_status_not_found(self):
        """Test getting status for non-existent artifact."""
        digest = (
            "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        status = self.manager.get_artifact_status(digest)
        self.assertIsNone(status)

    def test_record_test_result(self):
        """Test recording test results for an artifact."""
        digest = (
            "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        commit = "abc123def456"
        registry = "ghcr.io"
        repository = "test/repo"

        # Record artifact first
        self.manager.record_artifact(digest, commit, registry, repository)

        # Record test result
        self.manager.record_test_result(
            digest, "integration", "passed", "2024-01-23T10:00:00Z", "All tests passed"
        )

        # Verify test result
        results = self.manager.get_test_results(digest)
        self.assertIsNotNone(results)
        self.assertIn("integration", results)
        self.assertEqual(results["integration"]["status"], "passed")
        self.assertEqual(results["integration"]["details"], "All tests passed")

    def test_get_test_results_not_found(self):
        """Test getting test results for non-existent artifact."""
        digest = (
            "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        results = self.manager.get_test_results(digest)
        self.assertIsNone(results)


class TestArtifactManagerIntegration(unittest.TestCase):
    """Integration tests for artifact manager CLI."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_cli_workflow(self):
        """Test complete CLI workflow."""
        import subprocess

        digest = (
            "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        commit = "test123"
        registry = "ghcr.io"
        repository = "test/repo"

        # Record artifact
        result = subprocess.run(
            [
                "python",
                f"{self.original_cwd}/scripts/ci/artifact_manager.py",
                "record-artifact",
                "--digest",
                digest,
                "--commit",
                commit,
                "--registry",
                registry,
                "--repository",
                repository,
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)

        # Check existing artifact
        result = subprocess.run(
            [
                "python",
                f"{self.original_cwd}/scripts/ci/artifact_manager.py",
                "check-existing",
                "--registry",
                registry,
                "--repository",
                repository,
                "--commit",
                commit,
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)

        # Get digest
        result = subprocess.run(
            [
                "python",
                f"{self.original_cwd}/scripts/ci/artifact_manager.py",
                "get-digest",
                "--commit",
                commit,
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), digest)

    def test_cli_status_and_test_results_workflow(self):
        """Test CLI workflow for status updates and test results."""
        import subprocess

        digest = (
            "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        commit = "test123"
        registry = "ghcr.io"
        repository = "test/repo"

        # Record artifact
        result = subprocess.run(
            [
                "python",
                f"{self.original_cwd}/scripts/ci/artifact_manager.py",
                "record-artifact",
                "--digest",
                digest,
                "--commit",
                commit,
                "--registry",
                registry,
                "--repository",
                repository,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)

        # Update status
        result = subprocess.run(
            [
                "python",
                f"{self.original_cwd}/scripts/ci/artifact_manager.py",
                "update-status",
                "--digest",
                digest,
                "--status",
                "testing",
                "--timestamp",
                "2024-01-23T10:00:00Z",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)

        # Get status
        result = subprocess.run(
            [
                "python",
                f"{self.original_cwd}/scripts/ci/artifact_manager.py",
                "get-status",
                "--digest",
                digest,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "testing")

        # Record test result
        result = subprocess.run(
            [
                "python",
                f"{self.original_cwd}/scripts/ci/artifact_manager.py",
                "record-test-result",
                "--digest",
                digest,
                "--test-type",
                "integration",
                "--status",
                "passed",
                "--timestamp",
                "2024-01-23T10:00:00Z",
                "--details",
                "All tests passed",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)

        # Get test results
        result = subprocess.run(
            [
                "python",
                f"{self.original_cwd}/scripts/ci/artifact_manager.py",
                "get-test-results",
                "--digest",
                digest,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        
        # Parse JSON output
        import json
        results = json.loads(result.stdout)
        self.assertIn("integration", results)
        self.assertEqual(results["integration"]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
