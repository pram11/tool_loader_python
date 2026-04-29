"""User confirmation gate for dangerous built-in tools."""

from functools import wraps
from typing import Any, Callable


def require_confirmation(describe: Callable[..., str]) -> Callable:
    """Wrap a tool function to require explicit user approval before running.

    Args:
        describe: A callable that receives the same *args/**kwargs as the tool
                  and returns a human-readable description of the action.

    Returns:
        Decorator that injects a y/N prompt before the tool body executes.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            action = describe(*args, **kwargs)
            print(f"\n⚠️  다음 작업을 실행하려 합니다:\n  {action}")
            try:
                answer = input("계속하시겠습니까? [y/N]: ").strip().lower()
            except EOFError:
                answer = ""
            if answer != "y":
                return "사용자가 실행을 취소했습니다."
            return fn(*args, **kwargs)
        return wrapper
    return decorator
