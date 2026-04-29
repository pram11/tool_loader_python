import pytest
from tool_loader.security import CryptoManager
from tool_loader.registry import Registry
from tool_loader.models import ToolSchema, ToolType, TerminationPolicy
from tool_loader.exceptions import SystemToolError


@pytest.fixture
async def registry(tmp_path):
    key = CryptoManager.generate_key()
    crypto = CryptoManager(key=key)
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    reg = Registry(db_url=db_url, crypto=crypto)
    await reg.init_db()
    yield reg
    await reg.close()


@pytest.fixture
def sample_tool() -> ToolSchema:
    return ToolSchema(
        name="test_tool",
        type=ToolType.MCP,
        path_or_cmd="npx",
        args=["-y", "@some/mcp-server"],
        env_vars={"API_KEY": "my-secret"},
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="A test MCP tool.",
    )


async def test_add_and_get(registry: Registry, sample_tool: ToolSchema) -> None:
    added = await registry.add_tool(sample_tool)
    assert added.id is not None
    assert added.env_vars == {"API_KEY": "my-secret"}

    tools = await registry.get_enabled_tools()
    assert len(tools) == 1
    assert tools[0].name == "test_tool"
    assert tools[0].env_vars == {"API_KEY": "my-secret"}


async def test_toggle_tool(registry: Registry, sample_tool: ToolSchema) -> None:
    added = await registry.add_tool(sample_tool)
    await registry.toggle_tool(added.id, False)
    tools = await registry.get_enabled_tools()
    assert len(tools) == 0


async def test_system_tool_toggle_rejected(registry: Registry) -> None:
    system_tool = ToolSchema(
        name="system_tool",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.config_server:run",
        is_system=True,
    )
    added = await registry.add_tool(system_tool)
    with pytest.raises(SystemToolError):
        await registry.toggle_tool(added.id, False)


async def test_delete_normal_tool(registry: Registry, sample_tool: ToolSchema) -> None:
    added = await registry.add_tool(sample_tool)
    await registry.delete_tool(added.id)
    tools = await registry.get_all_tools()
    assert len(tools) == 0


async def test_delete_system_tool_rejected(registry: Registry) -> None:
    system_tool = ToolSchema(
        name="sys",
        type=ToolType.MCP,
        path_or_cmd="npx",
        is_system=True,
    )
    added = await registry.add_tool(system_tool)
    with pytest.raises(SystemToolError):
        await registry.delete_tool(added.id)
