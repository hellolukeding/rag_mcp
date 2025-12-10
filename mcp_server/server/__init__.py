"""Server package for MCP implementations.

This package exposes the `mcp_server` entry module. Previously it attempted
to import a non-existent `simple_mcp_server` which caused import-time
errors when the package was imported. Keep imports minimal and explicit.
"""

from . import mcp_server

__all__ = ["mcp_server"]
