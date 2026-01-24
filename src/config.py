"""Configuration management for Tailscale Paste Service.

This module handles loading configuration from environment variables and config files,
with sensible defaults for optional values.
"""

import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional
from typing import TypedDict

# Configure logging
logger = logging.getLogger(__name__)

# Handle tomllib/tomli for Python 3.11+ vs earlier versions
tomllib: ModuleType | None
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


class _ConfigValues(TypedDict):
    storage_path: str
    custom_domain: str | None
    listen_port: int
    tailscale_socket: str | None
    trust_proxy: bool


class ConfigError(Exception):
    """Raised when configuration is invalid or missing required values."""

    pass


class Config:
    """Configuration for the Tailscale Paste Service.

    Configuration is loaded with the following priority:
    1. Environment variables (highest priority)
    2. Configuration file (TOML format)
    3. Default values (lowest priority)

    Required configuration:
    - storage_path: Directory where pastes will be stored

    Optional configuration:
    - custom_domain: Custom domain for paste URLs (e.g., "paste.bytes.coffee")
    - listen_port: Port for HTTP server (default: 8080)
    - tailscale_socket: Path to Tailscale LocalAPI socket (auto-detected)
    """

    def __init__(
        self,
        storage_path: str,
        custom_domain: Optional[str] = None,
        listen_port: int = 8080,
        tailscale_socket: Optional[str] = None,
        trust_proxy: bool = False,
    ):
        """Initialize configuration with validated values.

        Args:
            storage_path: Directory where pastes will be stored
            custom_domain: Optional custom domain for paste URLs
            listen_port: Port for HTTP server
            tailscale_socket: Path to Tailscale LocalAPI socket

        Raises:
            ConfigError: If configuration values are invalid
        """
        self.storage_path = storage_path
        self.custom_domain = custom_domain
        self.listen_port = listen_port
        self.tailscale_socket = tailscale_socket or self._detect_tailscale_socket()
        self.trust_proxy = trust_proxy

    @classmethod
    def from_env_and_file(cls, config_file: Optional[str] = None) -> "Config":
        """Load configuration from environment variables and optional config file.

        Environment variables take precedence over config file values.

        Environment variables:
        - STORAGE_PATH: Directory for paste storage (required)
        - CUSTOM_DOMAIN: Custom domain for paste URLs (optional)
        - LISTEN_PORT: HTTP server port (optional, default: 8080)
        - TAILSCALE_SOCKET: Tailscale LocalAPI socket path (optional, auto-detected)

        Args:
            config_file: Path to TOML config file (optional)

        Returns:
            Config instance with loaded values

        Raises:
            ConfigError: If required configuration is missing or invalid
        """
        # Start with defaults (storage_path is required, no default)
        config_values: _ConfigValues = {
            "storage_path": "",  # Will be set from env/file or raise error
            "custom_domain": None,
            "listen_port": 8080,
            "tailscale_socket": None,
            "trust_proxy": False,
        }

        # Load from config file if provided
        if config_file:
            file_config = cls._load_from_file(config_file)
            config_values.update(file_config)

        # Override with environment variables
        if "STORAGE_PATH" in os.environ:
            config_values["storage_path"] = os.environ["STORAGE_PATH"]

        # Check if STORAGE_PATH is still empty (not provided via env or file)
        if not config_values["storage_path"]:
            raise ConfigError("STORAGE_PATH is required")
        if "CUSTOM_DOMAIN" in os.environ:
            config_values["custom_domain"] = os.environ["CUSTOM_DOMAIN"]
        if "LISTEN_PORT" in os.environ:
            try:
                config_values["listen_port"] = int(os.environ["LISTEN_PORT"])
            except ValueError:
                raise ConfigError("Invalid LISTEN_PORT: must be an integer")
        if "TAILSCALE_SOCKET" in os.environ:
            config_values["tailscale_socket"] = os.environ["TAILSCALE_SOCKET"]
        if "TRUST_PROXY" in os.environ:
            config_values["trust_proxy"] = os.environ["TRUST_PROXY"].lower() in {
                "1",
                "true",
                "yes",
                "on",
            }

        # Validate custom domain format if provided
        if config_values["custom_domain"]:
            cls._validate_custom_domain(config_values["custom_domain"])

        # Validate listen port
        if not (1 <= config_values["listen_port"] <= 65535):
            logger.error(f"Invalid listen_port: {config_values['listen_port']}")
            raise ConfigError("Invalid listen_port: must be between 1 and 65535")

        logger.info(
            f"Configuration loaded: storage_path={config_values['storage_path']}, "
            f"custom_domain={config_values['custom_domain']}, "
            f"listen_port={config_values['listen_port']}"
        )

        return cls(**config_values)

    @staticmethod
    def _load_from_file(config_file: str) -> _ConfigValues:
        """Load configuration from TOML file.

        Args:
            config_file: Path to TOML config file

        Returns:
            Dictionary of configuration values

        Raises:
            ConfigError: If file cannot be read or parsed
        """
        if tomllib is None:
            raise ConfigError(
                "TOML support not available. Install tomli for Python < 3.11"
            )

        try:
            with open(config_file, "rb") as f:
                data = tomllib.load(f)

            # Extract relevant configuration keys
            config: _ConfigValues = {
                "storage_path": "",  # Will be validated as required
                "custom_domain": None,
                "listen_port": 8080,
                "tailscale_socket": None,
                "trust_proxy": False,
            }
            if "storage_path" in data:
                config["storage_path"] = data["storage_path"]
            if "custom_domain" in data:
                config["custom_domain"] = data["custom_domain"]
            if "listen_port" in data:
                config["listen_port"] = data["listen_port"]
            if "tailscale_socket" in data:
                config["tailscale_socket"] = data["tailscale_socket"]
            if "trust_proxy" in data:
                config["trust_proxy"] = bool(data["trust_proxy"])

            return config

        except FileNotFoundError:
            raise ConfigError(f"Config file not found: {config_file}")
        except Exception as e:
            raise ConfigError(f"Failed to parse config file: {e}")

    @staticmethod
    def _validate_custom_domain(domain: str) -> None:
        """Validate custom domain format.

        Args:
            domain: Domain name to validate

        Raises:
            ConfigError: If domain format is invalid
        """
        if not domain:
            logger.error("Custom domain cannot be empty")
            raise ConfigError("Custom domain cannot be empty")

        # Basic validation: no protocol, no path, no port
        if "://" in domain:
            logger.error(f"Invalid custom domain (contains protocol): {domain}")
            raise ConfigError(
                "Custom domain should not include protocol (http:// or https://)"
            )
        if "/" in domain:
            logger.error(f"Invalid custom domain (contains path): {domain}")
            raise ConfigError("Custom domain should not include path")
        if domain.count(":") > 0:
            logger.error(f"Invalid custom domain (contains port): {domain}")
            raise ConfigError("Custom domain should not include port")

        # Check for valid characters (basic check)
        if not all(c.isalnum() or c in ".-" for c in domain):
            logger.error(f"Invalid custom domain (invalid characters): {domain}")
            raise ConfigError("Custom domain contains invalid characters")

        logger.debug(f"Custom domain validated: {domain}")

    @staticmethod
    def _detect_tailscale_socket() -> str:
        """Detect Tailscale LocalAPI socket path based on platform.

        Returns:
            Path to Tailscale LocalAPI socket
        """
        # Try common socket locations
        unix_socket = "/var/run/tailscale/tailscaled.sock"
        if os.path.exists(unix_socket):
            return unix_socket

        # Fall back to TCP for Windows/macOS
        return "localhost:41112"

    def validate_storage_path(self) -> None:
        """Validate that storage path exists and is writable.

        Raises:
            ConfigError: If storage path is invalid or not writable
        """
        path = Path(self.storage_path)

        # Create directory if it doesn't exist
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Storage path validated: {self.storage_path}")
        except Exception as e:
            logger.error(f"Cannot create storage directory: {e}")
            raise ConfigError(f"Cannot create storage directory: {e}")

        # Check if writable
        if not os.access(path, os.W_OK):
            logger.error(f"Storage path is not writable: {self.storage_path}")
            raise ConfigError(f"Storage path is not writable: {self.storage_path}")

    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"Config(storage_path={self.storage_path!r}, "
            f"custom_domain={self.custom_domain!r}, "
            f"listen_port={self.listen_port}, "
            f"tailscale_socket={self.tailscale_socket!r})"
        )
