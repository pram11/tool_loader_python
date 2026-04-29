"""Built-in file system tools for LangChain agents."""

import glob
import json
import os
from typing import List

from langchain_core.tools import tool

from ._confirmation import require_confirmation


@tool
def search_files(pattern: str, directory: str = ".") -> str:
    """Search for files matching a glob pattern within a directory.

    Args:
        pattern: Glob pattern (e.g. "**/*.py", "*.txt").
        directory: Root directory to search in. Defaults to current directory.

    Returns:
        JSON array of matching file paths, or an error message.
    """
    try:
        root = os.path.abspath(directory)
        if not os.path.isdir(root):
            return f"Error: '{directory}' is not a directory."
        matches = glob.glob(pattern, root_dir=root, recursive=True)
        return json.dumps(sorted(matches), ensure_ascii=False)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def list_directory(directory: str = ".", show_hidden: bool = False) -> str:
    """List the contents of a directory.

    Args:
        directory: Path to the directory. Defaults to current directory.
        show_hidden: Include entries whose names start with '.'.

    Returns:
        JSON array of objects with 'name', 'type' (file|directory), and 'size' (bytes).
    """
    try:
        root = os.path.abspath(directory)
        if not os.path.isdir(root):
            return f"Error: '{directory}' is not a directory."
        entries: List[dict] = []
        with os.scandir(root) as it:
            for entry in sorted(it, key=lambda e: e.name):
                if not show_hidden and entry.name.startswith("."):
                    continue
                info = entry.stat(follow_symlinks=False)
                entries.append({
                    "name": entry.name,
                    "type": "directory" if entry.is_dir(follow_symlinks=False) else "file",
                    "size": info.st_size,
                })
        return json.dumps(entries, ensure_ascii=False)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def read_file(file_path: str) -> str:
    """Read and return the text content of a file.

    Args:
        file_path: Path to the file.

    Returns:
        File content as a string, or an error message.
    """
    try:
        path = os.path.abspath(file_path)
        if not os.path.isfile(path):
            return f"Error: '{file_path}' does not exist."
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception as exc:
        return f"Error: {exc}"


def _describe_write(file_path: str, content: str) -> str:
    preview = content[:80].replace("\n", "\\n")
    ellipsis = "..." if len(content) > 80 else ""
    return f"Write file: {os.path.abspath(file_path)}\n  Content preview: {preview}{ellipsis}"


@tool
@require_confirmation(_describe_write)
def write_file(file_path: str, content: str) -> str:
    """Create or overwrite a file with the given text content.

    Requires user confirmation before writing.

    Args:
        file_path: Destination file path.
        content: Text content to write.

    Returns:
        Success message with the absolute path, or an error message.
    """
    try:
        path = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return f"Wrote {len(content)} characters to '{path}'."
    except Exception as exc:
        return f"Error: {exc}"


def _describe_delete(file_path: str) -> str:
    return f"Delete file: {os.path.abspath(file_path)}"


@tool
@require_confirmation(_describe_delete)
def delete_file(file_path: str) -> str:
    """Delete a file. Directories are not accepted.

    Requires user confirmation before deleting.

    Args:
        file_path: Path to the file to delete.

    Returns:
        Success message, or an error message.
    """
    try:
        path = os.path.abspath(file_path)
        if os.path.isdir(path):
            return f"Error: '{file_path}' is a directory. Provide a file path."
        if not os.path.exists(path):
            return f"Error: '{file_path}' does not exist."
        os.remove(path)
        return f"Deleted '{path}'."
    except Exception as exc:
        return f"Error: {exc}"
