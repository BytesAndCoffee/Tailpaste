#!/usr/bin/env python3
"""Main entry point for Tailscale Paste Service.

This module initializes all components and starts the HTTP server.
"""

import logging
import sys
from pathlib import Path

from src.app import run_server
from src.authenticator import Authenticator
from src.config import Config, ConfigError
from src.id_generator import IDGenerator
from src.paste_handler import PasteHandler
from src.renderer import Renderer
from src.storage import Storage, StorageError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the application."""
    logger.info("Starting Tailscale Paste Service...")

    try:
        # Load configuration from environment variables and config file
        logger.info("Loading configuration...")
        config_file = "config.toml" if Path("config.toml").exists() else None
        config = Config.from_env_and_file(config_file)
        logger.info(f"Configuration loaded: {config}")

        # Validate storage path exists and is writable
        logger.info("Validating storage path...")
        config.validate_storage_path()

        # Initialize Storage with validated database path
        logger.info("Initializing storage...")
        database_path = Path(config.storage_path) / "pastes.db"
        storage = Storage(str(database_path))
        logger.info(f"Storage initialized at: {database_path}")

        # Initialize Authenticator with Tailscale socket
        logger.info("Initializing authenticator...")
        authenticator = Authenticator(config.tailscale_socket)
        logger.info(f"Authenticator initialized with socket: {config.tailscale_socket}")

        # Initialize IDGenerator
        logger.info("Initializing ID generator...")
        id_generator = IDGenerator(id_length=8)
        logger.info("ID generator initialized")

        # Initialize PasteHandler with dependencies
        logger.info("Initializing paste handler...")
        paste_handler = PasteHandler(storage, id_generator, config)
        logger.info("Paste handler initialized")

        # Initialize Renderer
        logger.info("Initializing renderer...")
        renderer = Renderer()
        logger.info("Renderer initialized")

        # Start Flask server on configured port
        logger.info(f"Starting HTTP server on port {config.listen_port}...")
        logger.info(
            f"Custom domain: {config.custom_domain or 'Not configured (using default)'}"
        )
        logger.info("Service is ready to accept requests")

        run_server(config, authenticator, paste_handler, renderer)

    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your configuration and try again")
        sys.exit(1)
    except StorageError as e:
        logger.error(f"Storage initialization error: {e}")
        logger.error("Please check your storage path and database permissions")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected error during startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
