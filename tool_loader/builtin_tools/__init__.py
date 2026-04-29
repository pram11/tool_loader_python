"""Built-in tools bundled with tool_loader.

All tools are pre-registered as system tools (is_system=True) and can be
seeded into the Registry via seed_builtin_tools().

Dangerous tools (write_file, delete_file, execute_file, run_bash) prompt
for user confirmation via stdin before executing.
"""

from tool_loader.models import TerminationPolicy, ToolSchema, ToolType

from .file_tools import delete_file, list_directory, read_file, search_files, write_file
from .http_tools import http_request
from .shell_tools import execute_file, run_bash
from .system_tools import get_system_info

BUILTIN_MODULE = "tool_loader.builtin_tools"

BUILTIN_TOOLS: list[ToolSchema] = [
    ToolSchema(
        name="search_files",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.file_tools:search_files",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="Search for files matching a glob pattern.",
    ),
    ToolSchema(
        name="list_directory",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.file_tools:list_directory",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="List the contents of a directory.",
    ),
    ToolSchema(
        name="read_file",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.file_tools:read_file",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="Read and return the text content of a file.",
    ),
    ToolSchema(
        name="write_file",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.file_tools:write_file",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="[Confirmation required] Create or overwrite a file.",
    ),
    ToolSchema(
        name="delete_file",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.file_tools:delete_file",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="[Confirmation required] Delete a file.",
    ),
    ToolSchema(
        name="http_request",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.http_tools:http_request",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="Send an HTTP request (curl equivalent).",
    ),
    ToolSchema(
        name="execute_file",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.shell_tools:execute_file",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="[Confirmation required] Execute a script file.",
    ),
    ToolSchema(
        name="run_bash",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.shell_tools:run_bash",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="[Confirmation required] Run a bash command.",
    ),
    ToolSchema(
        name="get_system_info",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.system_tools:get_system_info",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="Return OS, CPU, and disk information.",
    ),
]

__all__ = [
    "BUILTIN_MODULE",
    "BUILTIN_TOOLS",
    "delete_file",
    "execute_file",
    "get_system_info",
    "http_request",
    "list_directory",
    "read_file",
    "run_bash",
    "search_files",
    "seed_builtin_tools",
    "write_file",
]


async def seed_builtin_tools(registry: "Registry") -> int:  # type: ignore[name-defined]  # noqa: F821
    """Register all built-in tools into the registry if not already present.

    Args:
        registry: An initialised Registry instance.

    Returns:
        Number of tools actually inserted (skips existing names).
    """
    from tool_loader.registry import Registry as _Registry  # local import to avoid circularity

    existing_names = {t.name for t in await registry.get_all_tools()}
    inserted = 0
    for schema in BUILTIN_TOOLS:
        if schema.name not in existing_names:
            await registry.add_tool(schema)
            inserted += 1
    return inserted
