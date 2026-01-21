"""Tests for Flask HTTP server.

Basic integration tests to verify Flask routes work correctly.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.app import create_app
from src.authenticator import (
    Authenticator,
    AuthenticationError,
    WhoIsInfo,
    UserProfile,
    Node,
)
from src.config import Config
from src.id_generator import IDGenerator
from src.paste_handler import PasteHandler
from src.renderer import Renderer
from src.storage import Storage


class TestFlaskApp:
    """Integration tests for Flask application."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_pastes.db"
            storage = Storage(str(db_path))
            yield storage

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config(
            storage_path="/tmp/test_pastes",
            custom_domain="paste.test.com",
            listen_port=8080,
        )

    @pytest.fixture
    def mock_authenticator(self):
        """Create mock authenticator."""
        return Mock(spec=Authenticator)

    @pytest.fixture
    def paste_handler(self, temp_storage, config):
        """Create paste handler with temp storage."""
        return PasteHandler(
            storage=temp_storage, id_generator=IDGenerator(), config=config
        )

    @pytest.fixture
    def renderer(self):
        """Create renderer."""
        return Renderer()

    @pytest.fixture
    def app(self, config, mock_authenticator, paste_handler, renderer):
        """Create Flask test app."""
        flask_app = create_app(config, mock_authenticator, paste_handler, renderer)
        flask_app.config["TESTING"] = True
        return flask_app

    @pytest.fixture
    def client(self, app):
        """Create Flask test client."""
        return app.test_client()

    @pytest.fixture
    def sample_whois_info(self):
        """Create sample WhoIsInfo."""
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

    def test_post_upload_success(self, client, mock_authenticator, sample_whois_info):
        """Test successful paste upload."""
        # Mock authenticator to return valid whois info
        mock_authenticator.verify_tailnet_source.return_value = sample_whois_info

        # Upload paste
        response = client.post("/", data="Hello, world!")

        # Verify response
        assert response.status_code == 200
        assert response.mimetype == "text/plain"
        assert "https://paste.test.com/" in response.get_data(as_text=True)

        # Verify authenticator was called
        mock_authenticator.verify_tailnet_source.assert_called_once()

    def test_post_upload_forbidden_non_tailnet(self, client, mock_authenticator):
        """Test upload rejection for non-tailnet source."""
        # Mock authenticator to raise authentication error
        mock_authenticator.verify_tailnet_source.side_effect = AuthenticationError(
            "Not from tailnet"
        )

        # Try to upload paste
        response = client.post("/", data="Test content")

        # Verify forbidden response
        assert response.status_code == 403
        assert b"Forbidden" in response.data
        assert b"tailnet" in response.data

    def test_post_upload_empty_content(
        self, client, mock_authenticator, sample_whois_info
    ):
        """Test upload rejection for empty content."""
        # Mock authenticator to return valid whois info
        mock_authenticator.verify_tailnet_source.return_value = sample_whois_info

        # Try to upload empty paste
        response = client.post("/", data="")

        # Verify bad request response
        assert response.status_code == 400
        assert b"Bad Request" in response.data
        assert b"empty" in response.data

    def test_post_upload_whitespace_only_content(
        self, client, mock_authenticator, sample_whois_info
    ):
        """Test upload rejection for whitespace-only content."""
        # Mock authenticator to return valid whois info
        mock_authenticator.verify_tailnet_source.return_value = sample_whois_info

        # Try to upload whitespace-only paste
        response = client.post("/", data="   \n\t  ")

        # Verify bad request response
        assert response.status_code == 400
        assert b"Bad Request" in response.data

    def test_post_upload_localapi_unreachable(self, client, mock_authenticator):
        """Test upload when LocalAPI is unreachable."""
        # Mock authenticator to raise connection error
        mock_authenticator.verify_tailnet_source.side_effect = AuthenticationError(
            "Failed to connect to Tailscale LocalAPI"
        )

        # Try to upload paste
        response = client.post("/", data="Test content")

        # Verify service unavailable response
        assert response.status_code == 503
        assert b"Service unavailable" in response.data

    def test_post_upload_content_too_large(
        self, client, mock_authenticator, sample_whois_info
    ):
        """Test upload rejection for content exceeding size limit."""
        # Mock authenticator to return valid whois info
        mock_authenticator.verify_tailnet_source.return_value = sample_whois_info

        # Create content larger than 1MB
        large_content = "x" * (1024 * 1024 + 1)  # 1MB + 1 byte

        # Try to upload large paste
        response = client.post("/", data=large_content)

        # Verify payload too large response
        assert response.status_code == 413
        assert b"Payload Too Large" in response.data
        assert b"1MB" in response.data

    def test_get_retrieve_paste_invalid_id_format(self, client):
        """Test retrieval with invalid paste ID format."""
        # Try to retrieve with very long ID
        long_id = "x" * 200
        response = client.get(f"/{long_id}")

        # Verify bad request response
        assert response.status_code == 400
        assert b"Bad Request" in response.data
        assert b"Invalid paste ID" in response.data

    def test_get_retrieve_paste_success(
        self, client, mock_authenticator, sample_whois_info
    ):
        """Test successful paste retrieval."""
        # First create a paste
        mock_authenticator.verify_tailnet_source.return_value = sample_whois_info
        upload_response = client.post("/", data="Test content for retrieval")

        # Extract paste ID from URL
        paste_url = upload_response.get_data(as_text=True).strip()
        paste_id = paste_url.split("/")[-1]

        # Retrieve the paste
        response = client.get(f"/{paste_id}")

        # Verify response
        assert response.status_code == 200
        assert b"Test content for retrieval" in response.data

    def test_get_retrieve_paste_not_found(self, client):
        """Test retrieval of non-existent paste."""
        # Try to retrieve non-existent paste
        response = client.get("/nonexistent123")

        # Verify not found response
        assert response.status_code == 404
        assert b"Not Found" in response.data

    def test_get_retrieve_paste_plain_text(
        self, client, mock_authenticator, sample_whois_info
    ):
        """Test paste retrieval with plain text format."""
        # Create a paste
        mock_authenticator.verify_tailnet_source.return_value = sample_whois_info
        upload_response = client.post("/", data="Plain text content")
        paste_url = upload_response.get_data(as_text=True).strip()
        paste_id = paste_url.split("/")[-1]

        # Retrieve with plain text Accept header
        response = client.get(f"/{paste_id}", headers={"Accept": "text/plain"})

        # Verify plain text response
        assert response.status_code == 200
        assert response.mimetype == "text/plain"
        assert b"Plain text content" in response.data

    def test_get_retrieve_paste_html(
        self, client, mock_authenticator, sample_whois_info
    ):
        """Test paste retrieval with HTML format."""
        # Create a paste
        mock_authenticator.verify_tailnet_source.return_value = sample_whois_info
        upload_response = client.post("/", data="HTML content")
        paste_url = upload_response.get_data(as_text=True).strip()
        paste_id = paste_url.split("/")[-1]

        # Retrieve with HTML Accept header
        response = client.get(f"/{paste_id}", headers={"Accept": "text/html"})

        # Verify HTML response
        assert response.status_code == 200
        assert response.mimetype == "text/html"
        assert b"<!DOCTYPE html>" in response.data
        assert b"HTML content" in response.data

    def test_post_upload_proxy_headers_rejected(
        self, mock_authenticator, paste_handler, renderer, config
    ):
        """Test that requests with proxy headers are rejected."""
        flask_app = create_app(config, mock_authenticator, paste_handler, renderer)
        flask_app.config["TESTING"] = True

        with flask_app.test_client() as client:
            # Test X-Forwarded-For header
            response = client.post(
                "/",
                data="Test content",
                content_type="text/plain",
                headers={"X-Forwarded-For": "192.168.1.100"},
            )

            assert response.status_code == 403
            assert b"Proxied requests not allowed" in response.data

            # Test X-Real-Ip header
            response = client.post(
                "/",
                data="Test content",
                content_type="text/plain",
                headers={"X-Real-Ip": "192.168.1.100"},
            )

            assert response.status_code == 403
            assert b"Proxied requests not allowed" in response.data

            # Test X-Forwarded-Proto header
            response = client.post(
                "/",
                data="Test content",
                content_type="text/plain",
                headers={"X-Forwarded-Proto": "https"},
            )

            assert response.status_code == 403
            assert b"Proxied requests not allowed" in response.data

            # Verify authenticator was NOT called for any of these
            mock_authenticator.verify_tailnet_source.assert_not_called()
