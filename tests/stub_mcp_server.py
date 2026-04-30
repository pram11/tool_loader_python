"""Minimal FastMCP server used as a subprocess stub for MCP integration tests."""
import asyncio

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("stub-test-server")


@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def greet(name: str) -> str:
    """Return a greeting message for the given name."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
