"""SQLite database storage for pastes.

This module handles persistence of paste content and metadata to a SQLite database.
"""

import logging
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when storage operations fail."""

    pass


@dataclass
class Paste:
    """Represents a paste with content and metadata.

    Attributes:
        id: Unique paste identifier
        content: The paste content
        created_at: Creation timestamp (ISO 8601 format)
        source_host: Tailscale hostname of uploader
        source_user: Tailscale user email/login name
    """

    id: str
    content: str
    created_at: str
    source_host: str
    source_user: str

    def to_dict(self) -> dict:
        """Convert paste to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Paste":
        """Create Paste from dictionary."""
        return cls(**data)


class Storage:
    """SQLite database storage for pastes.

    Stores paste content and metadata in a SQLite database with schema:
    CREATE TABLE pastes (
        id TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        source_host TEXT NOT NULL,
        source_user TEXT NOT NULL
    )
    """

    def __init__(self, database_path: str):
        """Initialize storage with database path.

        Args:
            database_path: Path to SQLite database file

        Raises:
            StorageError: If database initialization fails
        """
        self.database_path = Path(database_path)

        # Ensure parent directory exists
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Storage initialized at: {self.database_path}")
        except Exception as e:
            logger.error(f"Failed to create database directory: {e}")
            raise StorageError(f"Failed to create database directory: {e}")

        # Initialize database schema
        self.initialize()

    def initialize(self) -> None:
        """Create database and schema if not exists.

        Creates the pastes table with the required schema.

        Raises:
            StorageError: If schema initialization fails
        """
        try:
            conn = sqlite3.connect(str(self.database_path))
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pastes (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    source_host TEXT NOT NULL,
                    source_user TEXT NOT NULL
                )
            """)

            conn.commit()
            conn.close()
            logger.debug("Database schema initialized successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise StorageError(f"Failed to initialize database schema: {e}")
        except Exception as e:
            logger.error(f"Unexpected error initializing database: {e}")
            raise StorageError(f"Unexpected error initializing database: {e}")

    def save(self, paste_id: str, paste: Paste) -> None:
        """Save a paste to database.

        Inserts paste into the pastes table.

        Args:
            paste_id: Unique paste identifier
            paste: Paste object to save

        Raises:
            StorageError: If save operation fails
        """
        try:
            conn = sqlite3.connect(str(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO pastes (id, content, created_at, source_host, source_user)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    paste.id,
                    paste.content,
                    paste.created_at,
                    paste.source_host,
                    paste.source_user,
                ),
            )

            conn.commit()
            conn.close()
            logger.debug(f"Paste saved to database: {paste_id}")

        except sqlite3.IntegrityError as e:
            logger.warning(f"Attempted to save duplicate paste ID: {paste_id}")
            raise StorageError(f"Paste with ID {paste_id} already exists: {e}")
        except sqlite3.Error as e:
            logger.error(f"Database error saving paste {paste_id}: {e}")
            raise StorageError(f"Failed to save paste {paste_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving paste {paste_id}: {e}")
            raise StorageError(f"Unexpected error saving paste {paste_id}: {e}")

    def load(self, paste_id: str) -> Paste:
        """Load a paste from database.

        Queries paste from the pastes table by ID.

        Args:
            paste_id: Unique paste identifier

        Returns:
            Paste object with content and metadata

        Raises:
            StorageError: If paste doesn't exist or load fails
        """
        try:
            conn = sqlite3.connect(str(self.database_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, content, created_at, source_host, source_user
                FROM pastes
                WHERE id = ?
            """,
                (paste_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if row is None:
                logger.debug(f"Paste not found in database: {paste_id}")
                raise StorageError(f"Paste not found: {paste_id}")

            logger.debug(f"Paste loaded from database: {paste_id}")
            return Paste(
                id=row["id"],
                content=row["content"],
                created_at=row["created_at"],
                source_host=row["source_host"],
                source_user=row["source_user"],
            )

        except StorageError:
            raise
        except sqlite3.Error as e:
            logger.error(f"Database error loading paste {paste_id}: {e}")
            raise StorageError(f"Failed to load paste {paste_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading paste {paste_id}: {e}")
            raise StorageError(f"Unexpected error loading paste {paste_id}: {e}")

    def exists(self, paste_id: str) -> bool:
        """Check if a paste exists in database.

        Args:
            paste_id: Unique paste identifier

        Returns:
            True if paste exists, False otherwise
        """
        try:
            conn = sqlite3.connect(str(self.database_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 1 FROM pastes WHERE id = ? LIMIT 1
            """,
                (paste_id,),
            )

            result = cursor.fetchone()
            conn.close()

            return result is not None

        except sqlite3.Error:
            return False
        except Exception:
            return False
