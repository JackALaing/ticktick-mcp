#!/usr/bin/env python3
"""
TickTick MCP Server - HTTP/SSE Transport for Claude.ai Remote MCP.

This module provides an HTTP endpoint for the TickTick MCP server,
enabling integration with Claude.ai's remote MCP feature.

Usage:
    python -m ticktick_sdk.server_http

Environment Variables (required):
    TICKTICK_CLIENT_ID      - OAuth2 client ID
    TICKTICK_CLIENT_SECRET  - OAuth2 client secret  
    TICKTICK_ACCESS_TOKEN   - Access token from OAuth2 flow
    TICKTICK_USERNAME       - TickTick account email
    TICKTICK_PASSWORD       - TickTick account password

Optional:
    PORT                    - HTTP port (default: 8000, Railway sets this)
    HOST                    - Host to bind (default: 0.0.0.0)

Claude.ai Integration:
    Add this URL to Claude.ai's MCP settings:
    https://your-railway-url.up.railway.app/sse
"""

from __future__ import annotations

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for HTTP/SSE server."""
    # Get host/port from environment
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info("Starting TickTick MCP Server on %s:%s", host, port)
    logger.info("SSE endpoint for Claude.ai: http://%s:%s/sse", host, port)
    
    # Import and modify the mcp instance before running
    from ticktick_sdk.server import mcp

    # Update settings on the mcp instance for cloud deployment
    mcp.settings.host = host
    mcp.settings.port = port

    # For Railway/cloud deployments, disable DNS rebinding protection
    # since we're behind a reverse proxy with a different hostname
    mcp.settings.transport_security.enable_dns_rebinding_protection = False
    mcp.settings.transport_security.allowed_hosts = ["*"]
    mcp.settings.transport_security.allowed_origins = ["*"]

    # Run with SSE transport for Claude.ai compatibility
    # The SSE endpoint will be available at /sse by default
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
