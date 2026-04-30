import json
import pytest

from tool_loader.config_server import build_config_server
from tool_loader.models import ToolSchema, ToolType, TerminationPolicy
from tool_loader.registry import Registry
from tool_loader.security import CryptoManager
from tool_loader.exceptions import SystemToolError


@pytest.fixture
async def registry(tmp_path):
    key = CryptoManager.generate_key()
    crypto = CryptoManager(key=key)
    db_url = f"sqlite+aiosqlite:///{tmp_path}/cfg_test.db"
    reg = Registry(db_url=db_url, crypto=crypto)
    await reg.init_db()
    yield reg
    await reg.close()


@pytest.fixture
def server(registry):
    return build_config_server(registry)


async def _call(server, tool_name: str, **kwargs) -> dict:
    """Call a FastMCP tool by name and parse the JSON response."""
    fn = server._tool_manager._tools[tool_name].fn
    raw = await fn(**kwargs)
    return json.loads(raw)


# ------------------------------------------------------------------
# list_tools
# ------------------------------------------------------------------

async def test_list_tools_empty(server) -> None:
    result = await _call(server, "list_tools")
    assert result == []


async def test_list_tools_returns_added(server, registry) -> None:
    await registry.add_tool(ToolSchema(
        name="t1", type=ToolType.MCP, path_or_cmd="npx",
    ))
    result = await _call(server, "list_tools")
    assert len(result) == 1
    assert result[0]["name"] == "t1"


# ------------------------------------------------------------------
# add_tool via MCP
# ------------------------------------------------------------------

async def test_add_tool_via_server(server, registry) -> None:
    res = await _call(
        server, "add_tool",
        name="new_tool",
        type="mcp",
        path_or_cmd="npx",
        args='["-y", "@some/pkg"]',
        env_vars='{"KEY": "val"}',
        termination_policy="ON_DEMAND",
        description="Test tool",
    )
    assert res["ok"] is True
    assert res["name"] == "new_tool"
    tools = await registry.get_all_tools()
    assert len(tools) == 1
    assert tools[0].env_vars == {"KEY": "val"}


async def test_add_tool_invalid_type(server) -> None:
    res = await _call(
        server, "add_tool",
        name="bad",
        type="invalid_type",
        path_or_cmd="npx",
    )
    assert "error" in res


# ------------------------------------------------------------------
# toggle_tool via MCP
# ------------------------------------------------------------------

async def test_toggle_tool_via_server(server, registry) -> None:
    added = await registry.add_tool(ToolSchema(
        name="tog", type=ToolType.MCP, path_or_cmd="npx",
    ))
    res = await _call(server, "toggle_tool", tool_id=added.id, enabled=False)
    assert res["ok"] is True
    tools = await registry.get_enabled_tools()
    assert len(tools) == 0


async def test_toggle_system_tool_returns_error(server, registry) -> None:
    added = await registry.add_tool(ToolSchema(
        name="sys", type=ToolType.MCP, path_or_cmd="npx", is_system=True,
    ))
    res = await _call(server, "toggle_tool", tool_id=added.id, enabled=False)
    assert "error" in res


# ------------------------------------------------------------------
# delete_tool via MCP
# ------------------------------------------------------------------

async def test_delete_tool_via_server(server, registry) -> None:
    added = await registry.add_tool(ToolSchema(
        name="del_me", type=ToolType.MCP, path_or_cmd="npx",
    ))
    res = await _call(server, "delete_tool", tool_id=added.id)
    assert res["ok"] is True
    assert len(await registry.get_all_tools()) == 0


async def test_delete_system_tool_returns_error(server, registry) -> None:
    added = await registry.add_tool(ToolSchema(
        name="sys2", type=ToolType.MCP, path_or_cmd="npx", is_system=True,
    ))
    res = await _call(server, "delete_tool", tool_id=added.id)
    assert "error" in res


# ------------------------------------------------------------------
# get_tool via MCP
# ------------------------------------------------------------------

async def test_get_tool_by_id(server, registry) -> None:
    added = await registry.add_tool(ToolSchema(
        name="get_me", type=ToolType.MCP, path_or_cmd="npx",
        description="hello",
    ))
    res = await _call(server, "get_tool", tool_id=added.id)
    assert res["name"] == "get_me"
    assert res["description"] == "hello"


async def test_get_tool_not_found(server) -> None:
    res = await _call(server, "get_tool", tool_id=9999)
    assert "error" in res
