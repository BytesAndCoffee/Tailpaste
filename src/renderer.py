"""Response rendering for paste content.

This module handles rendering paste content in different formats (plain text and HTML)
with proper character escaping and content-type negotiation.
"""

import html
from typing import Literal

from src.storage import Paste

Format = Literal["plain", "html"]


class Renderer:
    """Renders paste content for HTTP responses.

    Provides methods to render pastes as plain text or HTML with proper
    character escaping, whitespace preservation, and content-type headers.
    """

    def render_plain_text(self, paste: Paste) -> tuple[str, str]:
        """Render paste as plain text.

        Returns the paste content as-is with plain text content-type.

        Args:
            paste: Paste object to render

        Returns:
            Tuple of (content, content_type)
        """
        return paste.content, "text/plain; charset=utf-8"

    def render_html(self, paste: Paste) -> tuple[str, str]:
        """Render paste as HTML with proper formatting.

        Escapes HTML special characters (<, >, &, ", ') to prevent injection,
        preserves whitespace using <pre> tags, and uses monospace font.

        Args:
            paste: Paste object to render

        Returns:
            Tuple of (html_content, content_type)
        """
        # Escape HTML special characters
        escaped_content = html.escape(paste.content, quote=True)

        # Build HTML document with proper formatting
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paste {paste.id}</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: 'Courier New', Courier, monospace;
            background-color: #f5f5f5;
        }}
        pre {{
            margin: 0;
            padding: 20px;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .metadata {{
            margin-bottom: 10px;
            padding: 10px;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 0.9em;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="metadata">
        <strong>Paste ID:</strong> {html.escape(paste.id)}<br>
        <strong>Created:</strong> {html.escape(paste.created_at)}<br>
        <strong>Source:</strong> {html.escape(paste.source_user)}@{html.escape(paste.source_host)}
    </div>
    <pre>{escaped_content}</pre>
</body>
</html>"""

        return html_content, "text/html; charset=utf-8"

    def determine_format(self, accept_header: str | None) -> Format:
        """Determine output format based on Accept header.

        Performs content-type negotiation to decide whether to render
        as plain text or HTML based on the client's Accept header.

        Args:
            accept_header: Value of the Accept HTTP header (or None)

        Returns:
            "html" if client accepts HTML, "plain" otherwise
        """
        if accept_header is None:
            return "plain"

        # Normalize to lowercase for comparison
        accept_lower = accept_header.lower()

        # Check if client explicitly accepts HTML
        # Common browser Accept headers include "text/html" with high priority
        if "text/html" in accept_lower:
            return "html"

        # Check for wildcard that would accept HTML
        if "*/*" in accept_lower and "text/html" not in accept_lower:
            # If wildcard but no explicit HTML, prefer plain text
            return "plain"

        # Default to plain text for all other cases
        return "plain"
