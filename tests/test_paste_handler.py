"""Tests for PasteHandler class.

Tests paste creation logic including ID generation, metadata construction,
storage integration, and URL generation.
"""

import tempfile
from pathlib import Path

import pytest

from src.authenticator import WhoIsInfo, UserProfile, Node
from src.config import Config
from src.id_generator import IDGenerator
from src.paste_handler import PasteHandler, PasteHandlerError
from src.storage import Storage


class TestPasteHandler:
    """Unit tests for PasteHandler."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_pastes.db"
            storage = Storage(str(db_path))
            yield storage

    @pytest.fixture
    def config_with_custom_domain(self):
        """Create config with custom domain."""
        return Config(
            storage_path="/tmp/pastes",
            custom_domain="paste.example.com",
            listen_port=8080,
        )

    @pytest.fixture
    def config_without_custom_domain(self):
        """Create config without custom domain."""
        return Config(storage_path="/tmp/pastes", custom_domain=None, listen_port=8080)

    @pytest.fixture
    def sample_whois_info(self):
        """Create sample WhoIsInfo for testing."""
        return WhoIsInfo(
            node=Node(id="node123", name="test-machine", addresses=["100.64.0.1"]),
            user_profile=UserProfile(
                id="user456",
                login_name="user@example.com",
                display_name="Test User",
                profile_pic_url="https://example.com/pic.jpg",
            ),
            caps=[],
        )

    def test_create_paste_success(
        self, temp_storage, config_with_custom_domain, sample_whois_info
    ):
        """Test successful paste creation."""
        handler = PasteHandler(
            storage=temp_storage,
            id_generator=IDGenerator(),
            config=config_with_custom_domain,
        )

        content = "Hello, world!"
        paste_id, paste_url = handler.create_paste(content, sample_whois_info)

        # Verify ID is generated
        assert paste_id
        assert len(paste_id) == 8

        # Verify URL uses custom domain
        assert paste_url == f"https://paste.example.com/{paste_id}"

        # Verify paste is saved to storage
        assert temp_storage.exists(paste_id)

        # Verify paste content and metadata
        paste = temp_storage.load(paste_id)
        assert paste.content == content
        assert paste.source_host == "test-machine"
        assert paste.source_user == "user@example.com"
        assert paste.created_at  # Timestamp should be set

    def test_create_paste_without_custom_domain(
        self, temp_storage, config_without_custom_domain, sample_whois_info
    ):
        """Test paste creation without custom domain uses default."""
        handler = PasteHandler(
            storage=temp_storage,
            id_generator=IDGenerator(),
            config=config_without_custom_domain,
        )

        content = "Test content"
        paste_id, paste_url = handler.create_paste(content, sample_whois_info)

        # Verify URL uses default domain
        assert paste_url == f"https://paste.tailscale.local/{paste_id}"

    def test_create_paste_empty_content_raises_error(
        self, temp_storage, config_with_custom_domain, sample_whois_info
    ):
        """Test that empty content raises error."""
        handler = PasteHandler(
            storage=temp_storage,
            id_generator=IDGenerator(),
            config=config_with_custom_domain,
        )

        with pytest.raises(PasteHandlerError, match="Paste content cannot be empty"):
            handler.create_paste("", sample_whois_info)

    def test_create_paste_extracts_metadata_correctly(
        self, temp_storage, config_with_custom_domain, sample_whois_info
    ):
        """Test that metadata is extracted correctly from WhoIsInfo."""
        handler = PasteHandler(
            storage=temp_storage,
            id_generator=IDGenerator(),
            config=config_with_custom_domain,
        )

        content = "Test with metadata"
        paste_id, _ = handler.create_paste(content, sample_whois_info)

        paste = temp_storage.load(paste_id)
        assert paste.source_host == sample_whois_info.node.name
        assert paste.source_user == sample_whois_info.user_profile.login_name

    def test_create_multiple_pastes_have_unique_ids(
        self, temp_storage, config_with_custom_domain, sample_whois_info
    ):
        """Test that multiple pastes get unique IDs."""
        handler = PasteHandler(
            storage=temp_storage,
            id_generator=IDGenerator(),
            config=config_with_custom_domain,
        )

        ids = set()
        for i in range(10):
            paste_id, _ = handler.create_paste(f"Content {i}", sample_whois_info)
            ids.add(paste_id)

        # All IDs should be unique
        assert len(ids) == 10

    def test_get_paste_success(
        self, temp_storage, config_with_custom_domain, sample_whois_info
    ):
        """Test successful paste retrieval."""
        handler = PasteHandler(
            storage=temp_storage,
            id_generator=IDGenerator(),
            config=config_with_custom_domain,
        )

        # Create a paste
        content = "Test retrieval content"
        paste_id, _ = handler.create_paste(content, sample_whois_info)

        # Retrieve the paste
        paste = handler.get_paste(paste_id)

        # Verify content matches
        assert paste.content == content
        assert paste.id == paste_id
        assert paste.source_host == "test-machine"
        assert paste.source_user == "user@example.com"

    def test_get_paste_not_found_raises_error(
        self, temp_storage, config_with_custom_domain
    ):
        """Test that retrieving non-existent paste raises error."""
        handler = PasteHandler(
            storage=temp_storage,
            id_generator=IDGenerator(),
            config=config_with_custom_domain,
        )

        # Try to retrieve non-existent paste
        with pytest.raises(PasteHandlerError, match="Failed to retrieve paste"):
            handler.get_paste("nonexist")
