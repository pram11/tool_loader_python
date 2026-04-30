"""Integration tests: UniversalLoader ↔ Registry (real SQLite DB).

These tests exercise the full read path:
  Registry (aiosqlite) → env_vars 복호화 → UniversalLoader → callable 반환
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from tool_loader.core.loader import LoadResult, UniversalLoader
from tool_loader.core.process_manager import ProcessManager
from tool_loader.exceptions import ToolLoadError
from tool_loader.models import TerminationPolicy, ToolSchema, ToolType
from tool_loader.registry import Registry
from tool_loader.security import CryptoManager


@pytest.fixture
async def registry(tmp_path):
    key = CryptoManager.generate_key()
    crypto = CryptoManager(key=key)
    db_url = f"sqlite+aiosqlite:///{tmp_path}/integ.db"
    reg = Registry(db_url=db_url, crypto=crypto)
    await reg.init_db()
    yield reg
    await reg.close()


@pytest.fixture
def pm():
    return MagicMock(spec=ProcessManager)


@pytest.fixture
def loader(registry, pm):
    return UniversalLoader(
        registry=registry,
        process_manager=pm,
        allowed_modules={"math", "os.path"},
    )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def _add(registry: Registry, **kwargs) -> ToolSchema:
    defaults = dict(
        name="tool",
        type=ToolType.PYTHON,
        path_or_cmd="math:gcd",
        env_vars={"SECRET": "abc"},
        is_enabled=True,
    )
    defaults.update(kwargs)
    return await registry.add_tool(ToolSchema(**defaults))


# ------------------------------------------------------------------
# Full roundtrip: DB → loader
# ------------------------------------------------------------------

async def test_python_tool_full_roundtrip(loader, registry) -> None:
    await _add(registry, name="gcd_tool", path_or_cmd="math:gcd")
    result: LoadResult = await loader.aload_all(safe_mode=False)
    import math
    assert math.gcd in result.tools
    assert result.failures == []


async def test_env_vars_survive_roundtrip(registry) -> None:
    """env_vars must be decrypted to plain dict after Registry roundtrip."""
    await _add(registry, name="env_tool", env_vars={"API_KEY": "supersecret"})
    tools = await registry.get_enabled_tools()
    assert tools[0].env_vars == {"API_KEY": "supersecret"}


async def test_disabled_tool_not_loaded(loader, registry) -> None:
    await _add(registry, name="disabled", is_enabled=False)
    result = await loader.aload_all()
    assert result.tools == []


async def test_multiple_tools_loaded(loader, registry) -> None:
    await _add(registry, name="t1", path_or_cmd="math:gcd")
    await _add(registry, name="t2", path_or_cmd="math:floor")
    result = await loader.aload_all(safe_mode=False)
    assert len(result.tools) == 2


# ------------------------------------------------------------------
# safe_mode + return_failures
# ------------------------------------------------------------------

async def test_safe_mode_bad_module_collected(loader, registry) -> None:
    # os module is not in allowed_modules (only "math" and "os.path")
    await _add(registry, name="bad_os", path_or_cmd="os:getcwd")
    result = await loader.aload_all(safe_mode=True, return_failures=True)
    assert result.tools == []
    assert len(result.failures) == 1
    assert result.failures[0].tool_name == "bad_os"


async def test_safe_mode_mixed_success_and_failure(loader, registry) -> None:
    await _add(registry, name="good", path_or_cmd="math:gcd")
    await _add(registry, name="bad", path_or_cmd="os:getcwd")
    result = await loader.aload_all(safe_mode=True, return_failures=True)
    import math
    assert math.gcd in result.tools
    assert len(result.failures) == 1
    assert result.failures[0].tool_name == "bad"


async def test_safe_mode_false_raises_on_first_failure(loader, registry) -> None:
    await _add(registry, name="bad", path_or_cmd="nonexistent_pkg:fn")
    with pytest.raises(ToolLoadError) as exc_info:
        await loader.aload_all(safe_mode=False)
    assert exc_info.value.tool_name == "bad"


async def test_return_failures_false_suppresses_list(loader, registry) -> None:
    await _add(registry, name="bad", path_or_cmd="os:getcwd")
    result = await loader.aload_all(safe_mode=True, return_failures=False)
    assert result.failures == []


# ------------------------------------------------------------------
# Whitelist edge cases
# ------------------------------------------------------------------

async def test_submodule_allowed_by_prefix(registry, pm) -> None:
    inner_loader = UniversalLoader(
        registry=registry,
        process_manager=pm,
        allowed_modules={"os"},
    )
    await _add(registry, name="path_tool", path_or_cmd="os.path:join")
    result = await inner_loader.aload_all(safe_mode=False)
    import os.path
    assert os.path.join in result.tools


async def test_exact_match_prefix_not_overly_broad(registry, pm) -> None:
    """'os' whitelist should NOT match 'os_something' module."""
    inner_loader = UniversalLoader(
        registry=registry,
        process_manager=pm,
        allowed_modules={"os"},
    )
    await _add(registry, name="fake", path_or_cmd="os_something:fn")
    result = await inner_loader.aload_all(safe_mode=True, return_failures=True)
    assert len(result.failures) == 1
