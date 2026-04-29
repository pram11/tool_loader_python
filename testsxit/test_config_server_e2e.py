"""
E2E tests for tool_loader.config_server over real MCP stdio transport.

Each test spawns the config_server as a subprocess and communicates
via the MCP JSON-RPC protocol, exercising the full stack:
    subprocess → FastMCP → Registry → SQLite
"""
import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from tool_loader.security import CryptoManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _params(tmp_path: Path, fernet_key: str) -> StdioServerParameters:
    db_url = f"sqlite+aiosqlite:///{tmp_path}/e2e.db"
    return StdioServerParameters(
        command=sys.executable,
        args=[
            "-m", "tool_loader.config_server",
            "--db-url", db_url,
            "--fernet-key", fernet_key,
        ],
        cwd=str(PROJECT_ROOT),
    )


async def _call(session: ClientSession, tool: str, **kwargs) -> dict:
    """Invoke an MCP tool and return the parsed JSON response."""
    result = await session.call_tool(tool, arguments=kwargs or None)
    return json.loads(result.content[0].text)


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────

@pytest.fixture
def fernet_key() -> str:
    return CryptoManager.generate_key().decode()


# ────────────────────────────────────────────────────────────────────
# Tests — read paths
# ────────────────────────────────────────────────────────────────────

async def test_e2e_list_empty(tmp_path, fernet_key) -> None:
    async with stdio_client(_params(tmp_path, fernet_key)) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await _call(session, "list_tools")
    assert result == []


async def test_e2e_get_tool_not_found(tmp_path, fernet_key) -> None:
    async with stdio_client(_params(tmp_path, fernet_key)) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await _call(session, "get_tool", tool_id=9999)
    assert "error" in result


# ────────────────────────────────────────────────────────────────────
# Tests — write paths
# ────────────────────────────────────────────────────────────────────

async def test_e2e_add_and_list(tmp_path, fernet_key) -> None:
    async with stdio_client(_params(tmp_path, fernet_key)) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()

            add_res = await _call(
                session, "add_tool",
                name="e2e_tool",
                type="mcp",
                path_or_cmd="npx",
                args='["-y", "@scope/pkg"]',
                env_vars='{"API_KEY": "secret123"}',
                termination_policy="ON_DEMAND",
                description="E2E test tool",
            )
            assert add_res["ok"] is True
            tool_id = add_res["id"]

            tools = await _call(session, "list_tools")
            assert len(tools) == 1
            assert tools[0]["name"] == "e2e_tool"
            assert tools[0]["id"] == tool_id


async def test_e2e_add_invalid_type_returns_error(tmp_path, fernet_key) -> None:
    async with stdio_client(_params(tmp_path, fernet_key)) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await _call(
                session, "add_tool",
                name="bad", type="invalid", path_or_cmd="npx",
            )
    assert "error" in result


async def test_e2e_get_tool_by_id(tmp_path, fernet_key) -> None:
    async with stdio_client(_params(tmp_path, fernet_key)) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()

            add_res = await _call(
                session, "add_tool",
                name="fetchable", type="python", path_or_cmd="src.math:add",
                description="a fetchable tool",
            )
            tool_id = add_res["id"]

            got = await _call(session, "get_tool", tool_id=tool_id)
            assert got["name"] == "fetchable"
            assert got["description"] == "a fetchable tool"
            assert got["type"] == "python"


async def test_e2e_toggle_disables_tool(tmp_path, fernet_key) -> None:
    async with stdio_client(_params(tmp_path, fernet_key)) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()

            add_res = await _call(
                session, "add_tool",
                name="toggler", type="mcp", path_or_cmd="npx",
            )
            tool_id = add_res["id"]

            toggle_res = await _call(session, "toggle_tool", tool_id=tool_id, enabled=False)
            assert toggle_res["ok"] is True

            # list_tools with enabled_only=True must exclude the disabled tool
            enabled = await _call(session, "list_tools", enabled_only=True)
            assert all(t["id"] != tool_id for t in enabled)

            # list_tools without filter must still show it
            all_tools = await _call(session, "list_tools")
            assert any(t["id"] == tool_id for t in all_tools)


async def test_e2e_delete_tool(tmp_path, fernet_key) -> None:
    async with stdio_client(_params(tmp_path, fernet_key)) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()

            add_res = await _call(
                session, "add_tool",
                name="doomed", type="mcp", path_or_cmd="npx",
            )
            tool_id = add_res["id"]

            del_res = await _call(session, "delete_tool", tool_id=tool_id)
            assert del_res["ok"] is True

            tools = await _call(session, "list_tools")
            assert tools == []


async def test_e2e_delete_nonexistent_tool(tmp_path, fernet_key) -> None:
    async with stdio_client(_params(tmp_path, fernet_key)) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await _call(session, "delete_tool", tool_id=9999)
    # Server wraps the exception as an error dict
    assert "error" in result
