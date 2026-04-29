import importlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Set

from langchain_mcp_adapters.client import MultiServerMCPClient

from tool_loader.exceptions import ModuleNotAllowedError, ToolLoadError
from tool_loader.models import ToolSchema, ToolType
from tool_loader.registry import Registry

from .process_manager import ProcessManager

logger = logging.getLogger(__name__)


@dataclass
class LoadResult:
    tools: List[Any] = field(default_factory=list)
    failures: List[ToolLoadError] = field(default_factory=list)


class UniversalLoader:
    """Loads LangChain-compatible tools from the registry.

    MCP tools are started via ProcessManager and adapted with
    langchain-mcp-adapters. Python tools are imported from allowed modules
    and wrapped as LangChain callables.

    Args:
        registry: Async Registry instance.
        process_manager: ProcessManager for MCP subprocess lifecycle.
        allowed_modules: Whitelist of importable module prefixes for Python tools.
    """

    def __init__(
        self,
        registry: Registry,
        process_manager: ProcessManager,
        allowed_modules: Set[str] | None = None,
    ) -> None:
        self._registry = registry
        self._pm = process_manager
        self._allowed_modules: Set[str] = allowed_modules or set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def aload_all(
        self, safe_mode: bool = True, return_failures: bool = False
    ) -> LoadResult:
        """Load all enabled tools from the registry.

        Args:
            safe_mode: If True, failures are collected instead of raised.
            return_failures: If True, populate LoadResult.failures.

        Returns:
            LoadResult with loaded tools and (optionally) failure details.
        """
        enabled: List[ToolSchema] = await self._registry.get_enabled_tools()
        result = LoadResult()

        for tool in enabled:
            try:
                loaded = await self._load_one(tool)
                result.tools.extend(loaded)
            except Exception as exc:
                error = ToolLoadError(tool.name, str(exc))
                logger.warning("Tool load failed: %s", error)
                if not safe_mode:
                    raise error from exc
                if return_failures:
                    result.failures.append(error)

        return result

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    async def _load_one(self, tool: ToolSchema) -> List[Any]:
        if tool.type == ToolType.MCP:
            return await self._load_mcp(tool)
        if tool.type == ToolType.PYTHON:
            return await self._load_python(tool)
        raise ToolLoadError(tool.name, f"Unknown tool type '{tool.type}'.")

    async def _load_mcp(self, tool: ToolSchema) -> List[Any]:
        proc = await self._pm.start(tool)
        if proc.returncode is not None:
            raise RuntimeError(f"Process exited immediately (code={proc.returncode}).")

        server_config: Dict[str, Any] = {
            tool.name: {
                "transport": "stdio",
                "command": tool.path_or_cmd,
                "args": tool.args,
                "env": tool.env_vars or None,
            }
        }
        client = MultiServerMCPClient(server_config)
        lc_tools = await client.get_tools()

        logger.info("Loaded %d MCP tool(s) from '%s'.", len(lc_tools), tool.name)
        return lc_tools

    async def _load_python(self, tool: ToolSchema) -> List[Any]:
        # path_or_cmd format: "module.submodule:callable_name"
        if ":" not in tool.path_or_cmd:
            raise ValueError(
                f"Python tool path must be 'module:callable', got '{tool.path_or_cmd}'."
            )
        module_path, attr = tool.path_or_cmd.rsplit(":", 1)

        self._validate_module(module_path, tool.name)

        module = importlib.import_module(module_path)
        callable_obj: Callable = getattr(module, attr)
        logger.info("Loaded Python callable '%s' from '%s'.", attr, module_path)
        return [callable_obj]

    def _validate_module(self, module_path: str, tool_name: str) -> None:
        if not self._allowed_modules:
            return
        if not any(
            module_path == allowed or module_path.startswith(allowed + ".")
            for allowed in self._allowed_modules
        ):
            raise ModuleNotAllowedError(
                f"Tool '{tool_name}': module '{module_path}' is not in the "
                f"allowed_modules whitelist: {self._allowed_modules}"
            )
