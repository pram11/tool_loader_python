import asyncio
import pytest

from tool_loader.core.process_manager import ProcessManager
from tool_loader.models import TerminationPolicy, ToolSchema, ToolType


def _make_tool(
    name: str = "echo_tool",
    policy: TerminationPolicy = TerminationPolicy.ON_DEMAND,
) -> ToolSchema:
    # Use 'cat' as a long-running process that reads stdin without deadlocking
    return ToolSchema(
        name=name,
        type=ToolType.MCP,
        path_or_cmd="cat",
        args=[],
        termination_policy=policy,
    )


@pytest.fixture
async def pm():
    manager = ProcessManager(idle_timeout=2.0)
    yield manager
    await manager.close_all()


# ------------------------------------------------------------------
# start / is_running
# ------------------------------------------------------------------

async def test_start_returns_process(pm: ProcessManager) -> None:
    tool = _make_tool()
    proc = await pm.start(tool)
    assert proc is not None
    assert proc.returncode is None
    assert pm.is_running(tool.name)


async def test_start_returns_cached_process(pm: ProcessManager) -> None:
    tool = _make_tool()
    proc1 = await pm.start(tool)
    proc2 = await pm.start(tool)
    assert proc1 is proc2  # same object — cache hit


async def test_stop_terminates_process(pm: ProcessManager) -> None:
    tool = _make_tool()
    proc = await pm.start(tool)
    await pm.stop(tool.name)
    assert not pm.is_running(tool.name)
    # process should be dead
    assert proc.returncode is not None


# ------------------------------------------------------------------
# idle timeout (ON_DEMAND)
# ------------------------------------------------------------------

async def test_idle_timeout_stops_process() -> None:
    pm = ProcessManager(idle_timeout=0.3)
    tool = _make_tool(policy=TerminationPolicy.ON_DEMAND)
    await pm.start(tool)
    assert pm.is_running(tool.name)
    await asyncio.sleep(0.6)
    assert not pm.is_running(tool.name)


async def test_start_resets_idle_timer(pm: ProcessManager) -> None:
    slow_pm = ProcessManager(idle_timeout=0.4)
    tool = _make_tool()
    await slow_pm.start(tool)
    await asyncio.sleep(0.25)
    # re-start (cache hit) resets timer
    await slow_pm.start(tool)
    await asyncio.sleep(0.25)
    # still alive — reset worked
    assert slow_pm.is_running(tool.name)
    await slow_pm.close_all()


# ------------------------------------------------------------------
# PERSISTENT policy — no idle timer
# ------------------------------------------------------------------

async def test_persistent_tool_stays_alive() -> None:
    pm = ProcessManager(idle_timeout=0.2)
    tool = _make_tool(policy=TerminationPolicy.PERSISTENT)
    await pm.start(tool)
    await asyncio.sleep(0.4)
    assert pm.is_running(tool.name)
    await pm.close_all()


# ------------------------------------------------------------------
# close_all
# ------------------------------------------------------------------

async def test_close_all_terminates_multiple(pm: ProcessManager) -> None:
    tools = [_make_tool(name=f"t{i}") for i in range(3)]
    for t in tools:
        await pm.start(t)
    await pm.close_all()
    for t in tools:
        assert not pm.is_running(t.name)


async def test_dead_process_restarts(pm: ProcessManager) -> None:
    tool = _make_tool()
    proc1 = await pm.start(tool)
    proc1.terminate()
    await proc1.wait()
    # next start should detect dead process and create a new one
    proc2 = await pm.start(tool)
    assert proc2 is not proc1
    assert proc2.returncode is None
