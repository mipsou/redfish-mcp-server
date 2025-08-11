"""
Redfish MCP Server

A Model Context Protocol server that provides tools for controlling
Redfish-enabled hardware and simulators.
"""

__version__ = "0.1.0"
__author__ = "Redfish MCP Server Contributors"

from .main import mcp

__all__ = ["mcp"]
