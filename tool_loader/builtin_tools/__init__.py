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
        description="글로브 패턴으로 파일을 검색합니다.",
    ),
    ToolSchema(
        name="list_directory",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.file_tools:list_directory",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="지정된 디렉토리의 내용을 조회합니다.",
    ),
    ToolSchema(
        name="read_file",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.file_tools:read_file",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="파일의 텍스트 내용을 읽어 반환합니다.",
    ),
    ToolSchema(
        name="write_file",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.file_tools:write_file",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="[확인 필요] 파일을 생성하거나 덮어씁니다.",
    ),
    ToolSchema(
        name="delete_file",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.file_tools:delete_file",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="[확인 필요] 파일을 삭제합니다.",
    ),
    ToolSchema(
        name="http_request",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.http_tools:http_request",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="HTTP 요청을 전송합니다 (curl 대체).",
    ),
    ToolSchema(
        name="execute_file",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.shell_tools:execute_file",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="[확인 필요] 스크립트 파일을 실행합니다.",
    ),
    ToolSchema(
        name="run_bash",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.shell_tools:run_bash",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="[확인 필요] bash 명령어를 실행합니다.",
    ),
    ToolSchema(
        name="get_system_info",
        type=ToolType.PYTHON,
        path_or_cmd="tool_loader.builtin_tools.system_tools:get_system_info",
        is_system=True,
        termination_policy=TerminationPolicy.ON_DEMAND,
        description="운영체제, CPU, 디스크 정보를 반환합니다.",
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
