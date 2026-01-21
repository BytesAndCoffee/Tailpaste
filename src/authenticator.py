"""Tailscale LocalAPI authentication for the Paste Service.

This module handles authentication by verifying that requests originate from
hosts on the user's tailnet using Tailscale's LocalAPI whois endpoint.
"""

import json
import logging
from typing import Dict, Any
from dataclasses import dataclass
from urllib.parse import quote

import requests
import requests_unixsocket

# Configure logging
logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails or LocalAPI is unreachable."""

    pass


@dataclass
class UserProfile:
    """Tailscale user profile information."""

    id: str
    login_name: str
    display_name: str
    profile_pic_url: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """Create UserProfile from whois response data."""
        return cls(
            id=data.get("ID", ""),
            login_name=data.get("LoginName", ""),
            display_name=data.get("DisplayName", ""),
            profile_pic_url=data.get("ProfilePicURL", ""),
        )


@dataclass
class Node:
    """Tailscale node information."""

    id: str
    name: str
    addresses: list[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Node":
        """Create Node from whois response data."""
        return cls(
            id=data.get("ID", ""),
            name=data.get("Name", ""),
            addresses=data.get("Addresses", []),
        )


@dataclass
class WhoIsInfo:
    """Complete whois information from Tailscale LocalAPI."""

    node: Node
    user_profile: UserProfile
    caps: list[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WhoIsInfo":
        """Create WhoIsInfo from whois response data."""
        return cls(
            node=Node.from_dict(data.get("Node", {})),
            user_profile=UserProfile.from_dict(data.get("UserProfile", {})),
            caps=data.get("CapMap", []),
        )


class Authenticator:
    """Authenticates requests using Tailscale LocalAPI.

    This class verifies that incoming requests originate from hosts on the
    user's tailnet by querying the Tailscale LocalAPI whois endpoint.
    """

    def __init__(self, tailscale_socket: str):
        """Initialize authenticator with Tailscale socket path.

        Args:
            tailscale_socket: Path to Tailscale LocalAPI socket
                             (Unix socket path or "host:port" for TCP)
        """
        self.tailscale_socket = tailscale_socket
        self._is_unix_socket = (
            ":" not in tailscale_socket or tailscale_socket.startswith("/")
        )

    def verify_tailnet_source(self, remote_addr: str) -> WhoIsInfo:
        """Verify that a remote address is from the tailnet.

        Queries Tailscale LocalAPI to get whois information for the remote address.
        If the query succeeds, the address is from the tailnet.

        Args:
            remote_addr: Remote IP address (with optional port, e.g., "100.64.0.1:12345")

        Returns:
            WhoIsInfo object containing user and node information

        Raises:
            AuthenticationError: If the address is not from tailnet or LocalAPI is unreachable
        """
        try:
            whois_data = self._query_whois(remote_addr)
            logger.debug(f"Successfully verified tailnet source: {remote_addr}")
            return WhoIsInfo.from_dict(whois_data)
        except requests.RequestException as e:
            logger.error(
                f"Failed to connect to Tailscale LocalAPI for {remote_addr}: {e}"
            )
            raise AuthenticationError(f"Failed to connect to Tailscale LocalAPI: {e}")
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Invalid whois response for {remote_addr}: {e}")
            raise AuthenticationError(f"Invalid whois response: {e}")

    def is_from_tailnet(self, remote_addr: str) -> bool:
        """Check if a remote address is from the tailnet.

        Args:
            remote_addr: Remote IP address (with optional port)

        Returns:
            True if address is from tailnet, False otherwise
        """
        try:
            self.verify_tailnet_source(remote_addr)
            return True
        except AuthenticationError:
            return False

    def _query_whois(self, remote_addr: str) -> Dict[str, Any]:
        """Query Tailscale LocalAPI whois endpoint.

        Args:
            remote_addr: Remote IP address to query

        Returns:
            Parsed JSON response from whois endpoint

        Raises:
            requests.RequestException: If request fails
            json.JSONDecodeError: If response is not valid JSON
        """
        if self._is_unix_socket:
            # Use Unix socket with requests-unixsocket
            # The LocalAPI requires Host: local-tailscaled.sock header
            session = requests_unixsocket.Session()
            socket_path_encoded = quote(self.tailscale_socket, safe="")
            url = f"http+unix://{socket_path_encoded}/localapi/v0/whois"
            headers = {"Host": "local-tailscaled.sock"}
            logger.debug(f"Using Unix socket URL: {url}")
            logger.debug(f"Socket path: {self.tailscale_socket}")
            logger.debug(f"Headers: {headers}")
        else:
            # Use TCP (Windows/macOS)
            session = requests.Session()
            url = f"http://{self.tailscale_socket}/localapi/v0/whois"
            headers = {}
            logger.debug(f"Using TCP URL: {url}")

        params = {"addr": remote_addr}
        logger.debug(f"Making whois request for {remote_addr} with params: {params}")

        try:
            if self._is_unix_socket:
                response = session.get(url, params=params, headers=headers, timeout=5)
            else:
                response = session.get(url, params=params, timeout=5)
            logger.debug(f"Response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Response content: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            logger.error(
                f"Response content: {getattr(e.response, 'text', 'No response content')}"
            )
            raise
