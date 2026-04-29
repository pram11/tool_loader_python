"""Built-in HTTP request tool for LangChain agents (curl equivalent)."""

import json
import urllib.error
import urllib.request
from typing import Any, Dict

from langchain_core.tools import tool


@tool
def http_request(
    url: str,
    method: str = "GET",
    headers: str = "{}",
    body: str = "",
    timeout: int = 30,
) -> str:
    """Send an HTTP request (curl equivalent).

    Args:
        url: Target URL.
        method: HTTP method — GET, POST, PUT, PATCH, DELETE, HEAD (default: GET).
        headers: JSON string of request headers (e.g. '{"Content-Type": "application/json"}').
        body: Request body string. For JSON APIs, pass the serialized JSON here.
        timeout: Request timeout in seconds (default 30).

    Returns:
        JSON object with 'status', 'headers', and 'body'.
    """
    try:
        parsed_headers: Dict[str, str] = json.loads(headers) if headers.strip() else {}
    except json.JSONDecodeError as exc:
        return f"Error: 'headers' is not valid JSON — {exc}"

    method = method.upper()
    body_bytes = body.encode("utf-8") if body else None

    req = urllib.request.Request(url, data=body_bytes, headers=parsed_headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_body = resp.read().decode("utf-8", errors="replace")
            resp_headers: Dict[str, Any] = dict(resp.headers)
            return json.dumps({
                "status": resp.status,
                "headers": resp_headers,
                "body": resp_body,
            }, ensure_ascii=False)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return json.dumps({
            "status": exc.code,
            "headers": dict(exc.headers) if exc.headers else {},
            "body": error_body,
            "error": str(exc),
        }, ensure_ascii=False)
    except urllib.error.URLError as exc:
        return f"Error: request failed — {exc.reason}"
    except TimeoutError:
        return f"Error: request timed out ({timeout}s)."
    except Exception as exc:
        return f"Error: {exc}"
