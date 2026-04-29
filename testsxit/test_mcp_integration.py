"""Integration tests: UniversalLoader with a real MCP stub server (stdio transport).

The stub server (stub_mcp_server.py) is spawned as a subprocess by
MultiServerMCPClient. ProcessManager is mocked to return a fake running
process, so only the MCP protocol layer is exercised end-to-end.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from tool_loader.core.loader import LoadResult, UniversalLoader
from tool_loader.core.process_manager import ProcessManager
from tool_loader.models import ToolSchema, ToolType
from tool_loader.registry import Registry
from tool_loader.security import CryptoManager

STUB_SERVER = Path(__file__).resolve().parent / "stub_mcp_server.py"


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
async def registry(tmp_path):
    key = CryptoManager.generate_key()
    crypto = CryptoManager(key=key)
    reg = Registry(db_url=f"sqlite+aiosqlite:///{tmp_path}/mcp_integ.db", crypto=crypto)
    await reg.init_db()
    yield reg
    await reg.close()


def _make_pm(returncode=None) -> MagicMock:
    """Build a ProcessManager mock whose start() simulates the given returncode."""
    pm = MagicMock(spec=ProcessManager)
    fake_proc = MagicMock()
    fake_proc.returncode = returncode
    pm.start = AsyncMock(return_value=fake_proc)
    return pm


@pytest.fixture
def live_pm():
    """Mock PM that reports the process as still running (returncode=None)."""
    return _make_pm(returncode=None)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


async def _add_stub_tool(registry: Registry, name: str = "stub_mcp") -> ToolSchema:
    return await registry.add_tool(
        ToolSchema(
            name=name,
            type=ToolType.MCP,
            path_or_cmd=sys.executable,
            args=[str(STUB_SERVER)],
            is_enabled=True,
        )
    )


# ──────────────────────────────────────────────────────────────────────────────
# Tool discovery
# ──────────────────────────────────────────────────────────────────────────────


async def test_stub_mcp_tools_discovered(registry, live_pm) -> None:
    """aload_all returns LangChain tools exposed by the real stub MCP server."""
    await _add_stub_tool(registry)
    loader = UniversalLoader(registry=registry, process_manager=live_pm)

    result: LoadResult = await loader.aload_all(safe_mode=False)

    names = {t.name for t in result.tools}
    assert "add_numbers" in names
    assert "greet" in names
    assert result.failures == []


async def test_stub_mcp_tool_count(registry, live_pm) -> None:
    """Exactly 2 tools should be discovered from the stub server."""
    await _add_stub_tool(registry)
    loader = UniversalLoader(registry=registry, process_manager=live_pm)

    result = await loader.aload_all(safe_mode=False)
    assert len(result.tools) == 2


async def test_stub_mcp_tool_descriptions_preserved(registry, live_pm) -> None:
    """LangChain tools carry the docstring descriptions from the stub server."""
    await _add_stub_tool(registry)
    loader = UniversalLoader(registry=registry, process_manager=live_pm)

    result = await loader.aload_all(safe_mode=False)
    descs = {t.name: (t.description or "").lower() for t in result.tools}
    assert "add" in descs.get("add_numbers", "")
    assert "greet" in descs.get("greet", "")


# ──────────────────────────────────────────────────────────────────────────────
# Error handling
# ──────────────────────────────────────────────────────────────────────────────


async def test_dead_process_raises_in_strict_mode(registry) -> None:
    """If the process exits immediately, aload_all(safe_mode=False) raises."""
    dead_pm = _make_pm(returncode=1)
    await _add_stub_tool(registry)
    loader = UniversalLoader(registry=registry, process_manager=dead_pm)

    with pytest.raises(Exception):
        await loader.aload_all(safe_mode=False)


async def test_dead_process_collected_in_safe_mode(registry) -> None:
    """A dead-process failure is silently collected when safe_mode=True."""
    dead_pm = _make_pm(returncode=1)
    await _add_stub_tool(registry)
    loader = UniversalLoader(registry=registry, process_manager=dead_pm)

    result = await loader.aload_all(safe_mode=True, return_failures=True)
    assert result.tools == []
    assert len(result.failures) == 1
    assert result.failures[0].tool_name == "stub_mcp"


async def test_bad_command_collected_in_safe_mode(registry, live_pm) -> None:
    """A nonexistent MCP server binary is collected as a failure in safe mode."""
    await registry.add_tool(
        ToolSchema(
            name="bad_server",
            type=ToolType.MCP,
            path_or_cmd="/nonexistent/binary",
            args=[],
            is_enabled=True,
        )
    )
    loader = UniversalLoader(registry=registry, process_manager=live_pm)

    result = await loader.aload_all(safe_mode=True, return_failures=True)
    assert result.tools == []
    assert len(result.failures) == 1
    assert result.failures[0].tool_name == "bad_server"


# ──────────────────────────────────────────────────────────────────────────────
# Multiple servers
# ──────────────────────────────────────────────────────────────────────────────


async def test_two_stub_servers_load_independently(registry, live_pm) -> None:
    """Two MCP server entries each contribute their own set of tools."""
    await _add_stub_tool(registry, name="stub_a")
    await _add_stub_tool(registry, name="stub_b")
    loader = UniversalLoader(registry=registry, process_manager=live_pm)

    result = await loader.aload_all(safe_mode=False)
    # Each stub exposes 2 tools → 4 total
    assert len(result.tools) == 4


async def test_mixed_mcp_and_python_tools(registry, live_pm) -> None:
    """MCP and Python tools coexist in the same load result."""
    await _add_stub_tool(registry, name="mcp_stub")
    await registry.add_tool(
        ToolSchema(
            name="math_tool",
            type=ToolType.PYTHON,
            path_or_cmd="math:gcd",
            is_enabled=True,
        )
    )
    loader = UniversalLoader(
        registry=registry,
        process_manager=live_pm,
        allowed_modules={"math"},
    )

    result = await loader.aload_all(safe_mode=False)
    # 2 MCP tools (add_numbers, greet) + 1 Python tool (math.gcd)
    assert len(result.tools) == 3
    import math
    assert math.gcd in result.tools
