"""Built-in system information tool for LangChain agents."""

import json
import os
import platform
import shutil

from langchain_core.tools import tool


@tool
def get_system_info() -> str:
    """Return current system information including OS, CPU, and disk usage.

    Returns:
        JSON object with 'os', 'cpu', and 'disk' sections.
    """
    try:
        uname = platform.uname()
        disk = shutil.disk_usage(os.path.abspath("/"))

        info = {
            "os": {
                "system": uname.system,
                "node": uname.node,
                "release": uname.release,
                "version": uname.version,
                "machine": uname.machine,
                "processor": uname.processor or platform.processor(),
                "python_version": platform.python_version(),
            },
            "cpu": {
                "logical_cores": os.cpu_count(),
                "architecture": platform.architecture()[0],
            },
            "disk": {
                "total_gb": round(disk.total / 1024 ** 3, 2),
                "used_gb": round(disk.used / 1024 ** 3, 2),
                "free_gb": round(disk.free / 1024 ** 3, 2),
                "used_percent": round(disk.used / disk.total * 100, 1),
            },
        }
        return json.dumps(info, ensure_ascii=False)
    except Exception as exc:
        return f"오류: {exc}"
