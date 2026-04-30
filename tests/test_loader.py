from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tool_loader.core.loader import LoadResult, UniversalLoader
from tool_loader.exceptions import ModuleNotAllowedError, ToolLoadError
from tool_loader.models import TerminationPolicy, ToolSchema, ToolType
from tool_loader.core.process_manager import ProcessManager


def _make_loader(tools: List[ToolSchema], allowed: set | None = None) -> UniversalLoader:
    registry = MagicMock()
    registry.get_enabled_tools = AsyncMock(return_value=tools)
    pm = MagicMock(spec=ProcessManager)
    return UniversalLoader(registry=registry, process_manager=pm, allowed_modules=allowed)


# ------------------------------------------------------------------
# Python tool loading
# ------------------------------------------------------------------

async def test_python_tool_loads_callable() -> None:
    tool = ToolSchema(
        name="math_add",
        type=ToolType.PYTHON,
        path_or_cmd="math:gcd",
    )
    loader = _make_loader([tool], allowed={"math"})
    result: LoadResult = await loader.aload_all(safe_mode=False)
    import math
    assert math.gcd in result.tools


async def test_python_tool_blocked_by_whitelist() -> None:
    tool = ToolSchema(
        name="os_tool",
        type=ToolType.PYTHON,
        path_or_cmd="os:getcwd",
    )
    loader = _make_loader([tool], allowed={"math"})
    result = await loader.aload_all(safe_mode=True, return_failures=True)
    assert len(result.tools) == 0
    assert len(result.failures) == 1
    assert isinstance(result.failures[0], ToolLoadError)


async def test_python_tool_no_whitelist_allows_all() -> None:
    tool = ToolSchema(
        name="os_tool",
        type=ToolType.PYTHON,
        path_or_cmd="os:getcwd",
    )
    loader = _make_loader([tool], allowed=None)
    result = await loader.aload_all(safe_mode=False)
    import os
    assert os.getcwd in result.tools


# ------------------------------------------------------------------
# safe_mode behaviour
# ------------------------------------------------------------------

async def test_safe_mode_collects_failures() -> None:
    tool = ToolSchema(
        name="bad_tool",
        type=ToolType.PYTHON,
        path_or_cmd="nonexistent_module:func",
    )
    loader = _make_loader([tool])
    result = await loader.aload_all(safe_mode=True, return_failures=True)
    assert len(result.failures) == 1


async def test_safe_mode_false_raises() -> None:
    tool = ToolSchema(
        name="bad_tool",
        type=ToolType.PYTHON,
        path_or_cmd="nonexistent_module:func",
    )
    loader = _make_loader([tool])
    with pytest.raises(ToolLoadError):
        await loader.aload_all(safe_mode=False)
