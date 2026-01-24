#!/usr/bin/env python3
"""
Artifact Manager - Utility for managing Docker artifact digests in CI/CD pipeline.

This script provides functionality for:
- Checking if artifacts already exist for a given commit
- Recording artifact metadata and digests
- Validating artifact digests
- Retrieving artifact information

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple


class ArtifactManager:
    """Manages Docker artifact lifecycle and digest operations."""

    def __init__(self):
        self.artifacts_file = Path(".artifacts.json")
        self.registry_cache = {}

    def load_artifacts(self) -> Dict:
        """Load existing artifact metadata from file."""
        if self.artifacts_file.exists():
            try:
                with open(self.artifacts_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load artifacts file: {e}", file=sys.stderr)
        return {"artifacts": {}, "metadata": {"version": "1.0"}}

    def save_artifacts(self, data: Dict) -> None:
        """Save artifact metadata to file."""
        try:
            with open(self.artifacts_file, "w") as f:
                json.dump(data, f, indent=2, sort_keys=True)
        except IOError as e:
            print(f"Error: Could not save artifacts file: {e}", file=sys.stderr)
            sys.exit(1)

    def validate_digest(self, digest: str) -> bool:
        """Validate that a digest follows the expected SHA256 format."""
        if not digest:
            return False

        # Docker digest format: sha256:64-character-hex-string
        pattern = r"^sha256:[a-f0-9]{64}$"
        return bool(re.match(pattern, digest))

    def validate_registry_access(self, registry: str, repository: str) -> bool:
        """Validate that we can access the container registry."""
        try:
            # Docker requires repository names to be lowercase
            repository_lower = repository.lower()
            # Try to get repository info using docker command
            cmd = ["docker", "manifest", "inspect", f"{registry}/{repository_lower}:latest"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False

    def check_existing_artifact(
        self, registry: str, repository: str, commit: str
    ) -> Optional[str]:
        """Check if an artifact already exists for the given commit."""
        data = self.load_artifacts()

        # Look for existing artifact by commit
        for artifact_id, artifact_info in data.get("artifacts", {}).items():
            if (
                artifact_info.get("commit") == commit
                and artifact_info.get("registry") == registry
                and artifact_info.get("repository") == repository
            ):
                return artifact_info.get("digest")

        return None

    def record_artifact(
        self, digest: str, commit: str, registry: str, repository: str
    ) -> None:
        """Record a new artifact with its metadata."""
        if not self.validate_digest(digest):
            print(f"Error: Invalid digest format: {digest}", file=sys.stderr)
            sys.exit(1)

        data = self.load_artifacts()

        # Create unique artifact ID
        artifact_id = f"{commit[:8]}-{digest.split(':')[1][:12]}"

        # Record artifact metadata
        data["artifacts"][artifact_id] = {
            "digest": digest,
            "commit": commit,
            "registry": registry,
            "repository": repository,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "created",
        }

        # Update metadata
        data["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        self.save_artifacts(data)
        print(f"Recorded artifact: {artifact_id} -> {digest}")

    def get_digest_for_commit(self, commit: str) -> Optional[str]:
        """Get the digest for a specific commit."""
        data = self.load_artifacts()

        for artifact_info in data.get("artifacts", {}).values():
            if artifact_info.get("commit") == commit:
                return artifact_info.get("digest")

        return None

    def validate_artifact_exists(
        self, digest: str, registry: str, repository: str
    ) -> bool:
        """Validate that an artifact exists in the registry."""
        if not self.validate_digest(digest):
            return False

        import time
        max_retries = 8  # Increased from 5 to allow more time for GHCR propagation
        retry_delay = 2  # seconds
        
        # Docker requires repository names to be lowercase
        repository_lower = repository.lower()
        
        for attempt in range(max_retries):
            try:
                # Use docker buildx imagetools inspect for better registry compatibility
                cmd = ["docker", "buildx", "imagetools", "inspect", f"{registry}/{repository_lower}@{digest}"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print(f"✓ Artifact validation successful on attempt {attempt + 1}", file=sys.stderr)
                    return True
                    
                # If not found and not last attempt, wait before retry
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1}/{max_retries} failed, retrying in {retry_delay}s...", file=sys.stderr)
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    # Last attempt failed
                    print(f"Attempt {attempt + 1}/{max_retries} failed (final attempt)", file=sys.stderr)
                    if result.stderr:
                        print(f"Error output: {result.stderr.strip()}", file=sys.stderr)
                    
            except subprocess.TimeoutExpired:
                if attempt < max_retries - 1:
                    print(f"Timeout on attempt {attempt + 1}/{max_retries}, retrying in {retry_delay}s...", file=sys.stderr)
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"Timeout on attempt {attempt + 1}/{max_retries} (final attempt)", file=sys.stderr)
                    
            except subprocess.SubprocessError as e:
                print(f"Subprocess error: {e}", file=sys.stderr)
                return False
                
        return False

    def update_artifact_status(
        self, digest: str, status: str, timestamp: str = None
    ) -> None:
        """Update the status of an existing artifact."""
        if not self.validate_digest(digest):
            print(f"Error: Invalid digest format: {digest}", file=sys.stderr)
            sys.exit(1)

        data = self.load_artifacts()

        # Find artifact by digest
        artifact_found = False
        for artifact_id, artifact_info in data.get("artifacts", {}).items():
            if artifact_info.get("digest") == digest:
                artifact_info["status"] = status
                artifact_info["status_updated_at"] = (
                    timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                )
                artifact_found = True
                print(f"Updated artifact {artifact_id} status to: {status}")
                break

        if not artifact_found:
            print(f"Warning: Artifact with digest {digest} not found", file=sys.stderr)
            return

        # Update metadata
        data["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        self.save_artifacts(data)

    def get_artifact_status(self, digest: str) -> Optional[str]:
        """Get the current status of an artifact."""
        data = self.load_artifacts()

        for artifact_info in data.get("artifacts", {}).values():
            if artifact_info.get("digest") == digest:
                return artifact_info.get("status")

        return None

    def record_test_result(
        self,
        digest: str,
        test_type: str,
        status: str,
        timestamp: str,
        details: str = None,
    ) -> None:
        """Record test results for an artifact."""
        if not self.validate_digest(digest):
            print(f"Error: Invalid digest format: {digest}", file=sys.stderr)
            sys.exit(1)

        data = self.load_artifacts()

        # Find artifact by digest
        artifact_found = False
        for artifact_id, artifact_info in data.get("artifacts", {}).items():
            if artifact_info.get("digest") == digest:
                # Initialize test_results if it doesn't exist
                if "test_results" not in artifact_info:
                    artifact_info["test_results"] = {}

                # Record test result
                artifact_info["test_results"][test_type] = {
                    "status": status,
                    "timestamp": timestamp,
                    "details": details,
                }

                artifact_found = True
                print(
                    f"Recorded {test_type} test result for artifact {artifact_id}: {status}"
                )
                break

        if not artifact_found:
            print(f"Warning: Artifact with digest {digest} not found", file=sys.stderr)
            return

        # Update metadata
        data["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        self.save_artifacts(data)

    def get_test_results(self, digest: str) -> Optional[Dict]:
        """Get test results for an artifact."""
        data = self.load_artifacts()

        for artifact_info in data.get("artifacts", {}).values():
            if artifact_info.get("digest") == digest:
                return artifact_info.get("test_results", {})

        return None

    def generate_content_hash(self, file_path: str) -> str:
        """Generate SHA256 hash of file content for validation."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return f"sha256:{sha256_hash.hexdigest()}"
        except IOError as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)
            sys.exit(1)
        """Generate SHA256 hash of file content for validation."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return f"sha256:{sha256_hash.hexdigest()}"
        except IOError as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)
            sys.exit(1)
        """Generate SHA256 hash of file content for validation."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return f"sha256:{sha256_hash.hexdigest()}"
        except IOError as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    """Main CLI interface for artifact management."""
    parser = argparse.ArgumentParser(description="Manage Docker artifacts and digests")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Check existing artifact command
    check_parser = subparsers.add_parser(
        "check-existing", help="Check if artifact exists for commit"
    )
    check_parser.add_argument(
        "--registry", required=True, help="Container registry URL"
    )
    check_parser.add_argument("--repository", required=True, help="Repository name")
    check_parser.add_argument("--commit", required=True, help="Git commit SHA")

    # Record artifact command
    record_parser = subparsers.add_parser(
        "record-artifact", help="Record new artifact metadata"
    )
    record_parser.add_argument("--digest", required=True, help="Artifact digest")
    record_parser.add_argument("--commit", required=True, help="Git commit SHA")
    record_parser.add_argument(
        "--registry", required=True, help="Container registry URL"
    )
    record_parser.add_argument("--repository", required=True, help="Repository name")

    # Get digest command
    get_parser = subparsers.add_parser("get-digest", help="Get digest for commit")
    get_parser.add_argument("--commit", required=True, help="Git commit SHA")

    # Validate digest command
    validate_parser = subparsers.add_parser(
        "validate-digest", help="Validate artifact digest"
    )
    validate_parser.add_argument(
        "--digest", required=True, help="Artifact digest to validate"
    )
    validate_parser.add_argument(
        "--registry", required=True, help="Container registry URL"
    )
    validate_parser.add_argument("--repository", required=True, help="Repository name")

    # Update status command
    status_parser = subparsers.add_parser(
        "update-status", help="Update artifact status"
    )
    status_parser.add_argument("--digest", required=True, help="Artifact digest")
    status_parser.add_argument("--status", required=True, help="New status")
    status_parser.add_argument("--timestamp", help="Status timestamp (ISO format)")

    # Get status command
    get_status_parser = subparsers.add_parser("get-status", help="Get artifact status")
    get_status_parser.add_argument("--digest", required=True, help="Artifact digest")

    # Record test result command
    test_result_parser = subparsers.add_parser(
        "record-test-result", help="Record test result for artifact"
    )
    test_result_parser.add_argument("--digest", required=True, help="Artifact digest")
    test_result_parser.add_argument(
        "--test-type", required=True, help="Type of test (unit, integration, etc.)"
    )
    test_result_parser.add_argument(
        "--status", required=True, help="Test status (passed, failed)"
    )
    test_result_parser.add_argument(
        "--timestamp", required=True, help="Test timestamp (ISO format)"
    )
    test_result_parser.add_argument("--details", help="Additional test details")

    # Get test results command
    get_test_results_parser = subparsers.add_parser(
        "get-test-results", help="Get test results for artifact"
    )
    get_test_results_parser.add_argument(
        "--digest", required=True, help="Artifact digest"
    )

    # Generate hash command
    hash_parser = subparsers.add_parser(
        "generate-hash", help="Generate content hash for file"
    )
    hash_parser.add_argument("--file", required=True, help="File path to hash")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    manager = ArtifactManager()

    try:
        if args.command == "check-existing":
            existing_digest = manager.check_existing_artifact(
                args.registry, args.repository, args.commit
            )
            if existing_digest:
                print(f"Existing artifact found: {existing_digest}")
                sys.exit(0)
            else:
                print("No existing artifact found")
                sys.exit(1)

        elif args.command == "record-artifact":
            manager.record_artifact(
                args.digest, args.commit, args.registry, args.repository
            )

        elif args.command == "get-digest":
            digest = manager.get_digest_for_commit(args.commit)
            if digest:
                print(digest)
            else:
                print(f"No digest found for commit: {args.commit}", file=sys.stderr)
                sys.exit(1)

        elif args.command == "validate-digest":
            if not manager.validate_digest(args.digest):
                print(f"Error: Invalid digest format: {args.digest}", file=sys.stderr)
                sys.exit(1)

            if manager.validate_artifact_exists(
                args.digest, args.registry, args.repository
            ):
                print(f"Artifact validated: {args.digest}")
            else:
                print(
                    f"Error: Artifact not found in registry: {args.digest}",
                    file=sys.stderr,
                )
                sys.exit(1)

        elif args.command == "update-status":
            manager.update_artifact_status(args.digest, args.status, args.timestamp)

        elif args.command == "get-status":
            status = manager.get_artifact_status(args.digest)
            if status:
                print(status)
            else:
                print(f"No status found for digest: {args.digest}", file=sys.stderr)
                sys.exit(1)

        elif args.command == "record-test-result":
            manager.record_test_result(
                args.digest, args.test_type, args.status, args.timestamp, args.details
            )

        elif args.command == "get-test-results":
            results = manager.get_test_results(args.digest)
            if results:
                print(json.dumps(results, indent=2))
            else:
                print(
                    f"No test results found for digest: {args.digest}", file=sys.stderr
                )
                sys.exit(1)

        elif args.command == "generate-hash":
            content_hash = manager.generate_content_hash(args.file)
            print(content_hash)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
