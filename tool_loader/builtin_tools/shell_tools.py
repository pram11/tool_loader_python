"""Built-in shell execution tools for LangChain agents."""

import json
import os
import shlex
import subprocess
import sys
from typing import Dict

from langchain_core.tools import tool

from ._confirmation import require_confirmation

_INTERPRETER_MAP: Dict[str, str] = {
    ".py": sys.executable,
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".fish": "fish",
    ".rb": "ruby",
    ".js": "node",
    ".ts": "ts-node",
    ".pl": "perl",
    ".php": "php",
}


def _describe_execute(file_path: str, args: str = "") -> str:
    abs_path = os.path.abspath(file_path)
    return f"Execute file: {abs_path}" + (f"  args: {args}" if args else "")


def _describe_bash(command: str, timeout: int = 30) -> str:
    return f"Run bash command: {command}"


@tool
@require_confirmation(_describe_execute)
def execute_file(file_path: str, args: str = "") -> str:
    """Execute a script file using an appropriate interpreter.

    Interpreter is chosen by file extension (.py → python, .sh → bash, etc.).
    Requires user confirmation before running.

    Args:
        file_path: Path to the script file.
        args: Optional space-separated arguments to pass to the script.

    Returns:
        JSON object with 'returncode', 'stdout', and 'stderr'.
    """
    try:
        path = os.path.abspath(file_path)
        if not os.path.isfile(path):
            return f"Error: '{file_path}' does not exist."

        _, ext = os.path.splitext(path)
        interpreter = _INTERPRETER_MAP.get(ext.lower())
        if not interpreter:
            return f"Error: '{ext}' is not a supported extension. Supported: {list(_INTERPRETER_MAP)}"

        cmd = [interpreter, path] + (shlex.split(args) if args.strip() else [])
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return json.dumps({
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return "Error: execution timed out (60s)."
    except Exception as exc:
        return f"Error: {exc}"


@tool
@require_confirmation(_describe_bash)
def run_bash(command: str, timeout: int = 30) -> str:
    """Run an arbitrary bash command and return its output.

    Requires user confirmation before running.

    Args:
        command: Shell command string to execute.
        timeout: Maximum execution time in seconds (default 30).

    Returns:
        JSON object with 'returncode', 'stdout', and 'stderr'.
    """
    try:
        proc = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return json.dumps({
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return f"Error: execution timed out ({timeout}s)."
    except Exception as exc:
        return f"Error: {exc}"
