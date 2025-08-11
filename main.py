#!/usr/bin/env python3
"""
Redfish MCP Server Entry Point

This file serves as the entry point for the Redfish MCP server.
It imports and runs the server from the modular structure.
"""

from src.redfish_mcp_server.main import mcp

if __name__ == "__main__":
    mcp.run()
