"""Built-in MCP server for managing tool_loader registry.

Exposes CRUD operations as MCP tools so that any connected LLM agent
can inspect and configure the tool registry at runtime without direct
Python access.

Usage (stdio transport, run as subprocess):
    python -m tool_loader.config_server --db-url sqlite+aiosqlite:///tools.db

Usage (in-process for testing):
    server = build_config_server(registry)
"""

import argparse
import asyncio
import json
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP

from tool_loader.exceptions import SystemToolError
from tool_loader.models import TerminationPolicy, ToolSchema, ToolType
from tool_loader.registry import Registry
from tool_loader.security import CryptoManager


def build_config_server(registry: Registry) -> FastMCP:
    """Create a FastMCP server wired to *registry*."""
    mcp = FastMCP("tool-loader-config")

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_tools(enabled_only: bool = False) -> str:
        """List all registered tools.

        Args:
            enabled_only: If true, return only enabled tools.
        """
        tools: List[ToolSchema] = (
            await registry.get_enabled_tools()
            if enabled_only
            else await registry.get_all_tools()
        )
        result = [
            {
                "id": t.id,
                "name": t.name,
                "type": t.type,
                "path_or_cmd": t.path_or_cmd,
                "args": t.args,
                "is_enabled": t.is_enabled,
                "is_system": t.is_system,
                "termination_policy": t.termination_policy,
                "description": t.description,
            }
            for t in tools
        ]
        return json.dumps(result, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def get_tool(tool_id: int) -> str:
        """Get a single tool by ID.

        Args:
            tool_id: The integer primary key of the tool.
        """
        tool = await registry.get_tool_by_id(tool_id)
        if tool is None:
            return json.dumps({"error": f"Tool id={tool_id} not found."})
        return json.dumps(
            {
                "id": tool.id,
                "name": tool.name,
                "type": tool.type,
                "path_or_cmd": tool.path_or_cmd,
                "args": tool.args,
                "is_enabled": tool.is_enabled,
                "is_system": tool.is_system,
                "termination_policy": tool.termination_policy,
                "description": tool.description,
            },
            ensure_ascii=False,
            indent=2,
        )

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    @mcp.tool()
    async def add_tool(
        name: str,
        type: str,
        path_or_cmd: str,
        args: str = "[]",
        env_vars: str = "{}",
        termination_policy: str = "ON_DEMAND",
        description: str = "",
    ) -> str:
        """Register a new tool in the registry.

        Args:
            name: Unique tool name.
            type: Tool type — 'mcp' or 'python'.
            path_or_cmd: Executable path (mcp) or 'module:callable' (python).
            args: JSON array of CLI arguments, e.g. '["-y", "@scope/pkg"]'.
            env_vars: JSON object of environment variables, e.g. '{"KEY": "val"}'.
            termination_policy: 'PERSISTENT' or 'ON_DEMAND'.
            description: Human-readable description.
        """
        try:
            tool = ToolSchema(
                name=name,
                type=ToolType(type),
                path_or_cmd=path_or_cmd,
                args=json.loads(args),
                env_vars=json.loads(env_vars),
                termination_policy=TerminationPolicy(termination_policy),
                description=description,
            )
        except Exception as exc:
            return json.dumps({"error": f"Validation error: {exc}"})

        try:
            added = await registry.add_tool(tool)
            return json.dumps({"ok": True, "id": added.id, "name": added.name})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool()
    async def toggle_tool(tool_id: int, enabled: bool) -> str:
        """Enable or disable a tool.

        Args:
            tool_id: The integer primary key of the tool.
            enabled: True to enable, False to disable.
        """
        try:
            await registry.toggle_tool(tool_id, enabled)
            return json.dumps({"ok": True, "tool_id": tool_id, "enabled": enabled})
        except SystemToolError as exc:
            return json.dumps({"error": str(exc)})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool()
    async def delete_tool(tool_id: int) -> str:
        """Permanently remove a tool from the registry.

        System tools cannot be deleted.

        Args:
            tool_id: The integer primary key of the tool.
        """
        try:
            await registry.delete_tool(tool_id)
            return json.dumps({"ok": True, "deleted_id": tool_id})
        except SystemToolError as exc:
            return json.dumps({"error": str(exc)})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    return mcp


async def _run(db_url: str, fernet_key: str) -> None:
    crypto = CryptoManager(key=fernet_key.encode())
    registry = Registry(db_url=db_url, crypto=crypto)
    await registry.init_db()
    try:
        mcp = build_config_server(registry)
        await mcp.run_async(transport="stdio")
    finally:
        await registry.close()


def run_config_server() -> None:
    """CLI entry point. Run via: python -m tool_loader.config_server"""
    parser = argparse.ArgumentParser(description="tool-loader config MCP server")
    parser.add_argument("--db-url", required=True, help="SQLAlchemy async DB URL")
    parser.add_argument("--fernet-key", required=True, help="Base64 Fernet key")
    args = parser.parse_args()
    asyncio.run(_run(args.db_url, args.fernet_key))
