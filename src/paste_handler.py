"""Paste creation and retrieval handler.

This module handles the core logic for creating and retrieving pastes,
including ID generation, metadata construction, and URL generation.
"""

import logging
from datetime import datetime, timezone

from src.authenticator import WhoIsInfo
from src.config import Config
from src.id_generator import IDGenerator
from src.storage import Paste, Storage

# Configure logging
logger = logging.getLogger(__name__)


class PasteHandlerError(Exception):
    """Raised when paste operations fail."""

    pass


class PasteHandler:
    """Handles paste creation and retrieval operations.

    This class coordinates between ID generation, storage, and URL construction
    to provide a high-level interface for paste operations.
    """

    def __init__(self, storage: Storage, id_generator: IDGenerator, config: Config):
        """Initialize paste handler with dependencies.

        Args:
            storage: Storage instance for persisting pastes
            id_generator: ID generator for creating unique paste IDs
            config: Configuration containing custom domain settings
        """
        self.storage = storage
        self.id_generator = id_generator
        self.config = config

    def create_paste(self, content: str, source_info: WhoIsInfo) -> tuple[str, str]:
        """Create a new paste with metadata.

        Generates a unique ID, constructs a Paste object with metadata
        (timestamp, source host, source user), saves it to storage, and
        returns the paste ID and public URL.

        Args:
            content: The paste content
            source_info: WhoIsInfo containing user and node information

        Returns:
            Tuple of (paste_id, paste_url)

        Raises:
            PasteHandlerError: If paste creation fails
        """
        # Validate content
        if not content:
            logger.warning("Attempted to create paste with empty content")
            raise PasteHandlerError("Paste content cannot be empty")

        # Generate unique ID
        try:
            paste_id = self.id_generator.generate(self.storage.exists)
            logger.debug(f"Generated paste ID: {paste_id}")
        except RuntimeError as e:
            logger.error(f"Failed to generate unique ID: {e}")
            raise PasteHandlerError(f"Failed to generate unique ID: {e}")

        # Get current timestamp in ISO 8601 format
        timestamp = datetime.now(timezone.utc).isoformat()

        # Extract source information from WhoIsInfo
        if not source_info:
            raise PasteHandlerError(
                "Authentication required: source information missing"
            )

        source_host = source_info.node.name
        source_user = source_info.user_profile.login_name

        # Construct Paste object
        paste = Paste(
            id=paste_id,
            content=content,
            created_at=timestamp,
            source_host=source_host,
            source_user=source_user,
        )

        # Save to storage
        try:
            self.storage.save(paste_id, paste)
            logger.info(f"Paste saved: {paste_id} by {source_user} from {source_host}")
        except Exception as e:
            logger.error(f"Failed to save paste {paste_id}: {e}")
            raise PasteHandlerError(f"Failed to save paste: {e}")

        # Generate and return paste URL
        paste_url = self._generate_url(paste_id)

        return paste_id, paste_url

    def get_paste(self, paste_id: str) -> Paste:
        """Retrieve a paste by ID.

        Loads paste from storage and returns the Paste object.

        Args:
            paste_id: Unique paste identifier

        Returns:
            Paste object with content and metadata

        Raises:
            PasteHandlerError: If paste doesn't exist or retrieval fails
        """
        try:
            paste = self.storage.load(paste_id)
            logger.debug(f"Paste retrieved: {paste_id}")
            return paste
        except Exception as e:
            logger.error(f"Failed to retrieve paste {paste_id}: {e}")
            raise PasteHandlerError(f"Failed to retrieve paste: {e}")

    def _generate_url(self, paste_id: str) -> str:
        """Generate public URL for a paste.

        Uses custom domain if configured, otherwise uses a placeholder
        that would be replaced with the actual Tailscale hostname
        in production.

        Args:
            paste_id: Unique paste identifier

        Returns:
            Full HTTPS URL to access the paste
        """
        if self.config.custom_domain:
            domain = self.config.custom_domain
        else:
            # In production, this would be the Tailscale hostname
            # For now, use a placeholder
            domain = "paste.tailscale.local"

        return f"https://{domain}/{paste_id}"
