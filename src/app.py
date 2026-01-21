"""Flask HTTP server for Tailscale Paste Service.

This module implements the HTTP server with routes for paste upload and retrieval.
"""

import logging
from flask import Flask, request, Response

from src.authenticator import Authenticator, AuthenticationError
from src.config import Config
from src.paste_handler import PasteHandler, PasteHandlerError
from src.renderer import Renderer
from src.storage import StorageError

# Configure logging
logger = logging.getLogger(__name__)

# Maximum paste size: 1MB
MAX_PASTE_SIZE = 1024 * 1024  # 1MB in bytes


def create_app(
    config: Config,
    authenticator: Authenticator,
    paste_handler: PasteHandler,
    renderer: Renderer,
) -> Flask:
    """Create and configure Flask application.

    Args:
        config: Configuration instance
        authenticator: Authenticator for verifying tailnet sources
        paste_handler: Handler for paste operations
        renderer: Renderer for formatting responses

    Returns:
        Configured Flask application
    """
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    def health_check():
        """Health check endpoint.

        GET / - Health check

        Returns:
            200: OK
        """
        return Response("OK\n", status=200, mimetype="text/plain")

    @app.route("/", methods=["POST"])
    def upload_paste():
        """Handle paste upload requests.

        POST / - Upload a new paste (tailnet-only)

        Returns:
            200: Paste URL on success
            400: Bad request (empty content)
            403: Forbidden (non-tailnet source)
            413: Payload too large
            500: Internal server error
            503: Service unavailable (LocalAPI unreachable)
        """
        # Extract remote IP from request
        remote_addr = request.remote_addr

        # Check for proxy headers that indicate request was forwarded
        proxy_headers = [
            "X-Forwarded-For",
            "X-Real-Ip",
            "X-Forwarded-Proto",
            "Via",
            "X-Forwarded-Host",
        ]
        detected_proxy_headers = [
            header for header in proxy_headers if header in request.headers
        ]

        if detected_proxy_headers:
            logger.warning(
                f"Proxy headers detected from {remote_addr}: {detected_proxy_headers}"
            )
            return Response(
                "Forbidden: Proxied requests not allowed. Connect directly via Tailscale.\n",
                status=403,
                mimetype="text/plain",
            )

        # Verify tailnet source for all requests
        try:
            source_info = authenticator.verify_tailnet_source(remote_addr)
        except AuthenticationError as e:
            logger.warning(f"Authentication failed for {remote_addr}: {e}")
            if "Failed to connect" in str(e):
                return Response(
                    "Service unavailable: Cannot connect to Tailscale LocalAPI\n",
                    status=503,
                    mimetype="text/plain",
                )
            return Response(
                "Forbidden: Uploads restricted to tailnet hosts\n",
                status=403,
                mimetype="text/plain",
            )

        # Check content size before reading
        content_length = request.content_length
        if content_length and content_length > MAX_PASTE_SIZE:
            logger.warning(
                f"Paste too large from {remote_addr}: {content_length} bytes"
            )
            return Response(
                f"Payload Too Large: Maximum paste size is {MAX_PASTE_SIZE} bytes (1MB)\n",
                status=413,
                mimetype="text/plain",
            )

        # Extract content from request body
        try:
            content = request.get_data(as_text=True)
        except Exception as e:
            logger.error(f"Failed to read request body from {remote_addr}: {e}")
            return Response(
                "Bad Request: Failed to read request body\n",
                status=400,
                mimetype="text/plain",
            )

        # Check actual content size (in case Content-Length header was missing)
        if len(content.encode("utf-8")) > MAX_PASTE_SIZE:
            logger.warning(
                f"Paste too large from {remote_addr}: {len(content.encode('utf-8'))} bytes"
            )
            return Response(
                f"Payload Too Large: Maximum paste size is {MAX_PASTE_SIZE} bytes (1MB)\n",
                status=413,
                mimetype="text/plain",
            )

        # Validate content is not empty
        if not content or content.strip() == "":
            logger.info(f"Empty paste rejected from {remote_addr}")
            return Response(
                "Bad Request: Paste content cannot be empty\n",
                status=400,
                mimetype="text/plain",
            )

        # Create paste
        try:
            paste_id, paste_url = paste_handler.create_paste(content, source_info)
            source_name = (
                source_info.user_profile.login_name
                if source_info
                else "tailscale-authenticated"
            )
            logger.info(f"Paste created: {paste_id} from {source_name}")
            return Response(f"{paste_url}\n", status=200, mimetype="text/plain")
        except PasteHandlerError as e:
            logger.error(f"Paste handler error for {remote_addr}: {e}")
            if "empty" in str(e).lower():
                return Response(
                    f"Bad Request: {e}\n", status=400, mimetype="text/plain"
                )
            return Response(
                f"Internal Server Error: {e}\n", status=500, mimetype="text/plain"
            )
        except StorageError as e:
            logger.error(f"Storage error for {remote_addr}: {e}")
            return Response(
                "Internal Server Error: Failed to save paste\n",
                status=500,
                mimetype="text/plain",
            )
        except Exception as e:
            logger.exception(f"Unexpected error for {remote_addr}: {e}")
            return Response(
                "Internal Server Error: An unexpected error occurred\n",
                status=500,
                mimetype="text/plain",
            )

    @app.route("/<paste_id>", methods=["GET"])
    def retrieve_paste(paste_id: str):
        """Handle paste retrieval requests.

        GET /<id> - Retrieve a paste (public access)

        Args:
            paste_id: Unique paste identifier from URL path

        Returns:
            200: Paste content (plain text or HTML)
            404: Not found
            500: Internal server error
        """
        # Validate paste ID format (basic validation)
        if not paste_id or len(paste_id) > 100:
            logger.warning(f"Invalid paste ID format: {paste_id}")
            return Response(
                "Bad Request: Invalid paste ID format\n",
                status=400,
                mimetype="text/plain",
            )

        # Retrieve paste
        try:
            paste = paste_handler.get_paste(paste_id)
            logger.info(f"Paste retrieved: {paste_id}")
        except PasteHandlerError as e:
            logger.info(f"Paste not found or retrieval failed: {paste_id} - {e}")
            if "not found" in str(e).lower() or "retrieve" in str(e).lower():
                return Response(
                    f"Not Found: Paste {paste_id} does not exist\n",
                    status=404,
                    mimetype="text/plain",
                )
            logger.error(f"Paste handler error for {paste_id}: {e}")
            return Response(
                "Internal Server Error: Failed to retrieve paste\n",
                status=500,
                mimetype="text/plain",
            )
        except StorageError as e:
            logger.info(f"Storage error for {paste_id}: {e}")
            if "not found" in str(e).lower():
                return Response(
                    f"Not Found: Paste {paste_id} does not exist\n",
                    status=404,
                    mimetype="text/plain",
                )
            logger.error(f"Storage error for {paste_id}: {e}")
            return Response(
                "Internal Server Error: Failed to retrieve paste\n",
                status=500,
                mimetype="text/plain",
            )
        except Exception as e:
            logger.exception(f"Unexpected error retrieving {paste_id}: {e}")
            return Response(
                "Internal Server Error: An unexpected error occurred\n",
                status=500,
                mimetype="text/plain",
            )

        # Determine format from Accept header
        try:
            accept_header = request.headers.get("Accept")
            format_type = renderer.determine_format(accept_header)

            # Render response
            if format_type == "html":
                content, content_type = renderer.render_html(paste)
            else:
                content, content_type = renderer.render_plain_text(paste)

            return Response(content, status=200, mimetype=content_type)
        except Exception as e:
            logger.exception(f"Error rendering paste {paste_id}: {e}")
            return Response(
                "Internal Server Error: Failed to render paste\n",
                status=500,
                mimetype="text/plain",
            )

    return app


def run_server(
    config: Config,
    authenticator: Authenticator,
    paste_handler: PasteHandler,
    renderer: Renderer,
) -> None:
    """Run the Flask HTTP server.

    Args:
        config: Configuration instance
        authenticator: Authenticator for verifying tailnet sources
        paste_handler: Handler for paste operations
        renderer: Renderer for formatting responses
    """
    app = create_app(config, authenticator, paste_handler, renderer)

    # Listen on all interfaces - Tailscale will handle routing
    # All requests will be authenticated via LocalAPI
    logger.info(f"Starting HTTP server on all interfaces, port {config.listen_port}")
    app.run(host="0.0.0.0", port=config.listen_port, debug=False)  # nosec B104
