"""Unit tests for main entry point and startup validation.

Tests startup validation including:
- Missing required configuration (storage path)
- Invalid custom domain format
- Successful startup with valid configuration
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


from src.config import Config, ConfigError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestStartupValidation:
    """Test startup validation scenarios."""

    def test_startup_failure_invalid_custom_domain_with_protocol(self):
        """Test that startup fails when custom domain includes protocol.

        Validates: Requirements 8.4
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {"STORAGE_PATH": tmpdir, "CUSTOM_DOMAIN": "https://paste.example.com"}

            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ConfigError) as exc_info:
                    Config.from_env_and_file()

                assert "protocol" in str(exc_info.value).lower()

    def test_startup_failure_invalid_custom_domain_with_path(self):
        """Test that startup fails when custom domain includes path.

        Validates: Requirements 8.4
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {"STORAGE_PATH": tmpdir, "CUSTOM_DOMAIN": "paste.example.com/path"}

            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ConfigError) as exc_info:
                    Config.from_env_and_file()

                assert "path" in str(exc_info.value).lower()

    def test_startup_failure_invalid_custom_domain_with_port(self):
        """Test that startup fails when custom domain includes port.

        Validates: Requirements 8.4
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {"STORAGE_PATH": tmpdir, "CUSTOM_DOMAIN": "paste.example.com:8080"}

            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ConfigError) as exc_info:
                    Config.from_env_and_file()

                assert "port" in str(exc_info.value).lower()

    def test_successful_startup_with_valid_config(self):
        """Test that startup succeeds with valid configuration.

        Validates: Requirements 8.4
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "STORAGE_PATH": tmpdir,
                "CUSTOM_DOMAIN": "paste.example.com",
                "LISTEN_PORT": "8080",
            }

            with patch.dict(os.environ, env, clear=True):
                config = Config.from_env_and_file()

                assert config.storage_path == tmpdir
                assert config.custom_domain == "paste.example.com"
                assert config.listen_port == 8080

                # Validate storage path
                config.validate_storage_path()

                # Verify storage path exists and is writable
                assert Path(tmpdir).exists()
                assert os.access(tmpdir, os.W_OK)

    def test_successful_startup_without_custom_domain(self):
        """Test that startup succeeds without custom domain (optional config).

        Validates: Requirements 8.4
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {"STORAGE_PATH": tmpdir}

            with patch.dict(os.environ, env, clear=True):
                config = Config.from_env_and_file()

                assert config.storage_path == tmpdir
                assert config.custom_domain is None
                assert config.listen_port == 8080  # Default value

    def test_storage_path_validation_creates_directory(self):
        """Test that storage path validation creates directory if it doesn't exist.

        Validates: Requirements 8.4
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a subdirectory path that doesn't exist yet
            storage_path = os.path.join(tmpdir, "pastes", "storage")

            env = {"STORAGE_PATH": storage_path}

            with patch.dict(os.environ, env, clear=True):
                config = Config.from_env_and_file()

                # Directory shouldn't exist yet
                assert not Path(storage_path).exists()

                # Validate storage path (should create it)
                config.validate_storage_path()

                # Now it should exist
                assert Path(storage_path).exists()
                assert os.access(storage_path, os.W_OK)

    def test_startup_failure_invalid_listen_port(self):
        """Test that startup fails with invalid listen port.

        Validates: Requirements 8.4
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {"STORAGE_PATH": tmpdir, "LISTEN_PORT": "99999"}  # Out of valid range

            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ConfigError) as exc_info:
                    Config.from_env_and_file()

                assert "listen_port" in str(exc_info.value).lower()
