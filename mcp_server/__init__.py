"""
MCP Server Module - Model Context Protocol server for Governance OS.

Exposes read-only tools for AI agents to access kernel state safely.
No write operations in v0 - all modifications require human approval.
"""

from .server import mcp, create_server

__all__ = ["mcp", "create_server"]
