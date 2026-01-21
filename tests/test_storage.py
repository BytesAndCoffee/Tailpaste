"""Property-based and unit tests for paste storage.

Feature: tailscale-paste-service
"""

import pytest
import tempfile
import os
from hypothesis import given, strategies as st, settings
from datetime import datetime

from src.storage import Storage, Paste, StorageError


@pytest.fixture
def temp_storage():
    """Create a temporary storage instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_pastes.db")
        storage = Storage(db_path)
        yield storage


class TestStorageProperties:
    """Property-based tests for storage operations."""

    @settings(max_examples=100)
    @given(
        content=st.text(min_size=1, max_size=10000),
        paste_id=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            min_size=8,
            max_size=8,
        ),
        source_host=st.text(min_size=1, max_size=100),
        source_user=st.text(min_size=1, max_size=100),
    )
    def test_property_4_paste_persistence(
        self, content, paste_id, source_host, source_user
    ):
        """Property 4: Paste persistence.

        For any paste that is successfully created, retrieving it by ID should
        return the same content that was originally uploaded.

        Validates: Requirements 2.3

        Feature: tailscale-paste-service, Property 4: Paste persistence
        """
        # Create temporary database for this test
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_pastes.db")
            storage = Storage(db_path)

            # Create a paste with random content
            created_at = datetime.utcnow().isoformat()
            original_paste = Paste(
                id=paste_id,
                content=content,
                created_at=created_at,
                source_host=source_host,
                source_user=source_user,
            )

            # Save the paste
            storage.save(paste_id, original_paste)

            # Retrieve the paste
            retrieved_paste = storage.load(paste_id)

            # Verify round-trip: retrieved content matches original
            assert (
                retrieved_paste.id == original_paste.id
            ), f"ID mismatch: expected {original_paste.id}, got {retrieved_paste.id}"
            assert (
                retrieved_paste.content == original_paste.content
            ), f"Content mismatch: expected {original_paste.content!r}, got {retrieved_paste.content!r}"
            assert (
                retrieved_paste.created_at == original_paste.created_at
            ), f"Timestamp mismatch: expected {original_paste.created_at}, got {retrieved_paste.created_at}"
            assert (
                retrieved_paste.source_host == original_paste.source_host
            ), f"Source host mismatch: expected {original_paste.source_host}, got {retrieved_paste.source_host}"
            assert (
                retrieved_paste.source_user == original_paste.source_user
            ), f"Source user mismatch: expected {original_paste.source_user}, got {retrieved_paste.source_user}"


class TestStorageUnitTests:
    """Unit tests for storage operations.

    Tests specific examples and edge cases for save, load, and exists operations.
    Requirements: 2.3, 2.4
    """

    def test_save_and_load_operations(self, temp_storage):
        """Test basic save and load operations work correctly."""
        # Create a paste
        paste = Paste(
            id="abc12345",
            content="Hello, world!",
            created_at="2024-01-01T12:00:00",
            source_host="test-host",
            source_user="test@example.com",
        )

        # Save the paste
        temp_storage.save("abc12345", paste)

        # Load the paste
        loaded_paste = temp_storage.load("abc12345")

        # Verify all fields match
        assert loaded_paste.id == paste.id
        assert loaded_paste.content == paste.content
        assert loaded_paste.created_at == paste.created_at
        assert loaded_paste.source_host == paste.source_host
        assert loaded_paste.source_user == paste.source_user

    def test_save_duplicate_id_raises_error(self, temp_storage):
        """Test that saving a paste with duplicate ID raises StorageError."""
        paste1 = Paste(
            id="duplicate1",
            content="First paste",
            created_at="2024-01-01T12:00:00",
            source_host="host1",
            source_user="user1@example.com",
        )

        paste2 = Paste(
            id="duplicate1",
            content="Second paste",
            created_at="2024-01-01T12:01:00",
            source_host="host2",
            source_user="user2@example.com",
        )

        # Save first paste
        temp_storage.save("duplicate1", paste1)

        # Attempt to save second paste with same ID should raise error
        with pytest.raises(StorageError) as exc_info:
            temp_storage.save("duplicate1", paste2)

        assert "already exists" in str(exc_info.value)

    def test_load_non_existent_paste_raises_error(self, temp_storage):
        """Test that loading a non-existent paste raises StorageError.

        Requirements: 2.3, 2.4
        """
        # Attempt to load a paste that doesn't exist
        with pytest.raises(StorageError) as exc_info:
            temp_storage.load("nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_exists_returns_true_for_existing_paste(self, temp_storage):
        """Test that exists() returns True for an existing paste.

        Requirements: 2.3, 2.4
        """
        # Create and save a paste
        paste = Paste(
            id="exists123",
            content="Test content",
            created_at="2024-01-01T12:00:00",
            source_host="test-host",
            source_user="test@example.com",
        )
        temp_storage.save("exists123", paste)

        # Check that it exists
        assert temp_storage.exists("exists123") is True

    def test_exists_returns_false_for_non_existent_paste(self, temp_storage):
        """Test that exists() returns False for a non-existent paste.

        Requirements: 2.3, 2.4
        """
        # Check that a non-existent paste returns False
        assert temp_storage.exists("doesnotexist") is False

    def test_save_with_special_characters(self, temp_storage):
        """Test saving and loading paste with special characters."""
        paste = Paste(
            id="special1",
            content="Line 1\nLine 2\tTabbed\r\nWindows line\n<html>&amp;</html>",
            created_at="2024-01-01T12:00:00",
            source_host="test-host",
            source_user="test@example.com",
        )

        temp_storage.save("special1", paste)
        loaded_paste = temp_storage.load("special1")

        # Verify special characters are preserved
        assert loaded_paste.content == paste.content

    def test_save_with_empty_content(self, temp_storage):
        """Test saving paste with empty content (should succeed at storage level)."""
        paste = Paste(
            id="empty123",
            content="",
            created_at="2024-01-01T12:00:00",
            source_host="test-host",
            source_user="test@example.com",
        )

        # Storage layer should accept empty content (validation happens at handler level)
        temp_storage.save("empty123", paste)
        loaded_paste = temp_storage.load("empty123")

        assert loaded_paste.content == ""

    def test_save_with_large_content(self, temp_storage):
        """Test saving and loading paste with large content."""
        # Create a large paste (100KB)
        large_content = "x" * 100000
        paste = Paste(
            id="large123",
            content=large_content,
            created_at="2024-01-01T12:00:00",
            source_host="test-host",
            source_user="test@example.com",
        )

        temp_storage.save("large123", paste)
        loaded_paste = temp_storage.load("large123")

        assert loaded_paste.content == large_content
        assert len(loaded_paste.content) == 100000
