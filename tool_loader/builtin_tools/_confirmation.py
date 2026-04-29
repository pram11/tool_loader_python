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
            print(f"\n⚠️  About to perform the following action:\n  {action}")
            try:
                answer = input("Continue? [y/N]: ").strip().lower()
            except EOFError:
                answer = ""
            if answer != "y":
                return "Action cancelled by user."
            return fn(*args, **kwargs)
        return wrapper
    return decorator
