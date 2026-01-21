"""Unit tests for Tailscale LocalAPI authenticator."""

import pytest
from unittest.mock import Mock, patch
import json

from src.authenticator import (
    Authenticator,
    AuthenticationError,
    WhoIsInfo,
    UserProfile,
    Node,
)


class TestDataStructures:
    """Test whois data structure parsing."""

    def test_user_profile_from_dict(self):
        """Test UserProfile creation from dictionary."""
        data = {
            "ID": "user123",
            "LoginName": "user@example.com",
            "DisplayName": "Test User",
            "ProfilePicURL": "https://example.com/pic.jpg",
        }
        profile = UserProfile.from_dict(data)

        assert profile.id == "user123"
        assert profile.login_name == "user@example.com"
        assert profile.display_name == "Test User"
        assert profile.profile_pic_url == "https://example.com/pic.jpg"

    def test_node_from_dict(self):
        """Test Node creation from dictionary."""
        data = {
            "ID": "node456",
            "Name": "test-machine",
            "Addresses": ["100.64.0.1", "fd7a:115c:a1e0::1"],
        }
        node = Node.from_dict(data)

        assert node.id == "node456"
        assert node.name == "test-machine"
        assert node.addresses == ["100.64.0.1", "fd7a:115c:a1e0::1"]

    def test_whois_info_from_dict(self):
        """Test WhoIsInfo creation from complete whois response."""
        data = {
            "Node": {
                "ID": "node456",
                "Name": "test-machine",
                "Addresses": ["100.64.0.1"],
            },
            "UserProfile": {
                "ID": "user123",
                "LoginName": "user@example.com",
                "DisplayName": "Test User",
                "ProfilePicURL": "https://example.com/pic.jpg",
            },
            "CapMap": ["cap1", "cap2"],
        }
        whois = WhoIsInfo.from_dict(data)

        assert whois.node.id == "node456"
        assert whois.user_profile.id == "user123"
        assert whois.caps == ["cap1", "cap2"]


class TestAuthenticator:
    """Test Authenticator class."""

    def test_init_unix_socket(self):
        """Test initialization with Unix socket path."""
        auth = Authenticator("/var/run/tailscale/tailscaled.sock")
        assert auth.tailscale_socket == "/var/run/tailscale/tailscaled.sock"
        assert auth._is_unix_socket is True

    def test_init_tcp_socket(self):
        """Test initialization with TCP socket."""
        auth = Authenticator("localhost:41112")
        assert auth.tailscale_socket == "localhost:41112"
        assert auth._is_unix_socket is False

    @patch("src.authenticator.requests.Session.get")
    def test_verify_tailnet_source_success(self, mock_get):
        """Test successful verification of tailnet source."""
        # Mock successful whois response
        mock_response = Mock()
        mock_response.json.return_value = {
            "Node": {
                "ID": "node456",
                "Name": "test-machine",
                "Addresses": ["100.64.0.1"],
            },
            "UserProfile": {
                "ID": "user123",
                "LoginName": "user@example.com",
                "DisplayName": "Test User",
                "ProfilePicURL": "https://example.com/pic.jpg",
            },
            "CapMap": [],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        auth = Authenticator("localhost:41112")
        whois = auth.verify_tailnet_source("100.64.0.1:12345")

        assert whois.node.name == "test-machine"
        assert whois.user_profile.login_name == "user@example.com"
        mock_get.assert_called_once()

    @patch("src.authenticator.requests.get")
    def test_verify_tailnet_source_connection_error(self, mock_get):
        """Test handling of LocalAPI connection errors."""
        import requests

        mock_get.side_effect = requests.RequestException("Connection refused")

        auth = Authenticator("localhost:41112")

        with pytest.raises(AuthenticationError) as exc_info:
            auth.verify_tailnet_source("192.168.1.1:12345")

        assert "Failed to connect to Tailscale LocalAPI" in str(exc_info.value)

    @patch("src.authenticator.requests.Session.get")
    def test_verify_tailnet_source_invalid_json(self, mock_get):
        """Test handling of invalid JSON responses."""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        auth = Authenticator("localhost:41112")

        with pytest.raises(AuthenticationError) as exc_info:
            auth.verify_tailnet_source("100.64.0.1:12345")

        assert "Invalid whois response" in str(exc_info.value)

    @patch("src.authenticator.requests.Session.get")
    def test_is_from_tailnet_true(self, mock_get):
        """Test is_from_tailnet returns True for tailnet hosts."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Node": {"ID": "node456", "Name": "test", "Addresses": []},
            "UserProfile": {
                "ID": "user123",
                "LoginName": "user@example.com",
                "DisplayName": "Test",
                "ProfilePicURL": "",
            },
            "CapMap": [],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        auth = Authenticator("localhost:41112")
        assert auth.is_from_tailnet("100.64.0.1:12345") is True

    @patch("src.authenticator.requests.Session.get")
    def test_is_from_tailnet_false(self, mock_get):
        """Test is_from_tailnet returns False for non-tailnet hosts."""
        import requests

        mock_get.side_effect = requests.RequestException("Connection refused")

        auth = Authenticator("localhost:41112")
        assert auth.is_from_tailnet("192.168.1.1:12345") is False
