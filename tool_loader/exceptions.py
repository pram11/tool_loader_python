class ToolLoaderError(Exception):
    """Base exception for tool_loader."""


class DecryptionError(ToolLoaderError):
    """Raised when Fernet decryption fails."""


class EncryptionError(ToolLoaderError):
    """Raised when Fernet encryption fails."""


class SystemToolError(ToolLoaderError):
    """Raised when attempting to mutate a system-protected tool."""


class ModuleNotAllowedError(ToolLoaderError):
    """Raised when a python tool's module is not in the allowed_modules whitelist."""


class ProcessDeadlockError(ToolLoaderError):
    """Raised when a subprocess stream stalls and deadlock is detected."""


class ToolLoadError(ToolLoaderError):
    """Raised when a tool fails to load during aload_all."""

    def __init__(self, tool_name: str, reason: str) -> None:
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"Failed to load '{tool_name}': {reason}")
