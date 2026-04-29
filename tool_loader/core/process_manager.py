import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from tool_loader.models import TerminationPolicy, ToolSchema

logger = logging.getLogger(__name__)


@dataclass
class _ManagedProcess:
    tool_name: str
    process: asyncio.subprocess.Process
    policy: str
    # background drain tasks
    _drain_tasks: List[asyncio.Task] = field(default_factory=list)
    # idle timer task (ON_DEMAND only)
    _idle_task: Optional[asyncio.Task] = None


class ProcessManager:
    """Manages MCP subprocess lifecycles.

    ON_DEMAND tools stay alive for `idle_timeout` seconds after their last
    use to avoid cold-start penalty. PERSISTENT tools run until close_all().

    Deadlocks are prevented by continuously draining stdout/stderr in
    background asyncio tasks.
    """

    def __init__(self, idle_timeout: float = 300.0) -> None:
        self._idle_timeout = idle_timeout
        self._procs: Dict[str, _ManagedProcess] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self, tool: ToolSchema) -> asyncio.subprocess.Process:
        """Start (or return cached) process for *tool*."""
        if tool.name in self._procs:
            managed = self._procs[tool.name]
            if managed.process.returncode is None:
                self._reset_idle_timer(tool.name)
                return managed.process
            # process died — clean up and restart
            await self._cleanup(tool.name)

        cmd = [tool.path_or_cmd, *tool.args]
        env = tool.env_vars if tool.env_vars else None
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        managed = _ManagedProcess(
            tool_name=tool.name,
            process=proc,
            policy=tool.termination_policy,
        )
        managed._drain_tasks = [
            asyncio.create_task(self._drain(proc.stdout, tool.name, "stdout")),
            asyncio.create_task(self._drain(proc.stderr, tool.name, "stderr")),
        ]
        self._procs[tool.name] = managed

        if tool.termination_policy == TerminationPolicy.ON_DEMAND:
            self._reset_idle_timer(tool.name)

        logger.info("Started process for tool '%s' (pid=%d)", tool.name, proc.pid)
        return proc

    async def stop(self, tool_name: str) -> None:
        """Gracefully terminate a single tool process."""
        await self._cleanup(tool_name)

    async def close_all(self) -> None:
        """Terminate all managed processes (call on application shutdown)."""
        for name in list(self._procs):
            await self._cleanup(name)

    def is_running(self, tool_name: str) -> bool:
        managed = self._procs.get(tool_name)
        return managed is not None and managed.process.returncode is None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reset_idle_timer(self, tool_name: str) -> None:
        managed = self._procs.get(tool_name)
        if managed is None:
            return
        if managed._idle_task and not managed._idle_task.done():
            managed._idle_task.cancel()
        managed._idle_task = asyncio.create_task(
            self._idle_shutdown(tool_name, self._idle_timeout)
        )

    async def _idle_shutdown(self, tool_name: str, timeout: float) -> None:
        await asyncio.sleep(timeout)
        logger.info("Idle timeout reached for '%s' — stopping process.", tool_name)
        await self._cleanup(tool_name)

    async def _cleanup(self, tool_name: str) -> None:
        managed = self._procs.pop(tool_name, None)
        if managed is None:
            return

        # cancel idle timer
        if managed._idle_task and not managed._idle_task.done():
            managed._idle_task.cancel()

        # cancel drain tasks
        for task in managed._drain_tasks:
            if not task.done():
                task.cancel()

        proc = managed.process
        if proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass
        logger.info("Process for tool '%s' stopped.", tool_name)

    @staticmethod
    async def _drain(
        stream: Optional[asyncio.StreamReader], tool_name: str, label: str
    ) -> None:
        """Continuously read stream to prevent pipe buffer deadlocks."""
        if stream is None:
            return
        try:
            while True:
                chunk = await stream.read(4096)
                if not chunk:
                    break
                logger.debug("[%s/%s] %s", tool_name, label, chunk.decode(errors="replace").rstrip())
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("Drain error for %s/%s: %s", tool_name, label, exc)
