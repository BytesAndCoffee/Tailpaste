"""Paste ID generation using base62 encoding.

This module generates unique, URL-friendly paste IDs using base62 encoding
(a-zA-Z0-9) with collision detection.
"""

import secrets
import string
from typing import Callable


class IDGenerator:
    """Generates unique paste IDs using base62 encoding.

    IDs are 8 characters long using a-zA-Z0-9, providing ~218 trillion
    possible combinations. Collision detection is performed by checking
    if an ID already exists before returning it.
    """

    # Base62 alphabet: a-zA-Z0-9
    BASE62_ALPHABET = string.ascii_letters + string.digits

    def __init__(self, id_length: int = 8):
        """Initialize ID generator.

        Args:
            id_length: Length of generated IDs (default: 8)
        """
        self.id_length = id_length

    def generate(self, exists_check: Callable[[str], bool]) -> str:
        """Generate a unique paste ID with collision detection.

        Generates random base62 IDs until one is found that doesn't already exist.
        Uses cryptographically secure random number generation.

        Args:
            exists_check: Function that returns True if an ID already exists

        Returns:
            A unique paste ID string

        Raises:
            RuntimeError: If unable to generate unique ID after many attempts
                         (extremely unlikely with 8-character base62)
        """
        max_attempts = 1000

        for _ in range(max_attempts):
            paste_id = self._generate_random_id()

            # Check for collision
            if not exists_check(paste_id):
                return paste_id

        # This should be extremely rare with 8-character base62
        raise RuntimeError(
            f"Failed to generate unique ID after {max_attempts} attempts. "
            "This indicates a serious problem with the storage system."
        )

    def _generate_random_id(self) -> str:
        """Generate a random base62 ID.

        Returns:
            Random ID string of specified length
        """
        return "".join(
            secrets.choice(self.BASE62_ALPHABET) for _ in range(self.id_length)
        )
