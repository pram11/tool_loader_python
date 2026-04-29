# tool-loader-python

An async tool loader library for managing tool metadata via SQLite and loading tools for LangChain agents.

> 한국어 문서: [README_KR.md](README_KR.md)

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# 1. Generate a Fernet encryption key (once)
python -m tool_loader keygen

# 2. Set environment variables
export TOOL_LOADER_FERNET_KEY=<key from step 1>
export TOOL_LOADER_DB_URL=sqlite+aiosqlite:///tools.db   # optional, this is the default

# 3. Register a tool and list it
python -m tool_loader add --name my_calc --type python --path "math:gcd" --description "Compute GCD"
python -m tool_loader list

# 4. Load all active tools and print results
python -m tool_loader load --allowed-modules math
```

## Architecture Overview

```
CryptoManager → Registry (SQLite) → UniversalLoader → LangChain Tools
                                  ↗
                   ProcessManager (MCP subprocesses)
```

| Component | Role |
|---|---|
| `CryptoManager` | Encrypts/decrypts `env_vars` with a Fernet symmetric key |
| `Registry` | Tool CRUD via SQLAlchemy + aiosqlite |
| `ProcessManager` | Lifecycle management for MCP server subprocesses |
| `UniversalLoader` | Loads MCP / Python tools into LangChain format |
| `config_server` | Embedded FastMCP server for runtime tool management |

---

## CLI Usage

Run subcommands via `python -m tool_loader <subcommand>`.  
All subcommands share the global options `--db-url` and `--fernet-key`, which can be replaced by environment variables.

```
python -m tool_loader [-h] [--db-url URL] [--fernet-key KEY] SUBCOMMAND
```

| Subcommand | Description | Key Options |
|---|---|---|
| `keygen` | Generate and print a Fernet key | — |
| `list` | List registered tools | `--enabled-only` |
| `add` | Register a tool | `--name`, `--type`, `--path`, `--args`, `--env`, `--policy`, `--description` |
| `delete` | Delete a tool | `TOOL_ID` |
| `toggle` | Enable or disable a tool | `TOOL_ID`, `--enable` \| `--disable` |
| `load` | Load all active tools and print results | `--allowed-modules`, `--seed-builtins` |
| `serve` | Run the config MCP server over stdio | (fernet-key required) |

```bash
# Generate a key
python -m tool_loader keygen

# Register an MCP tool
python -m tool_loader add \
  --name filesystem_mcp \
  --type mcp \
  --path npx \
  --args '["-y","@modelcontextprotocol/server-filesystem","/tmp"]' \
  --policy PERSISTENT

# List tools (active only)
python -m tool_loader list --enabled-only

# Disable / enable a tool
python -m tool_loader toggle 3 --disable
python -m tool_loader toggle 3 --enable

# Delete a tool
python -m tool_loader delete 3

# Start the config MCP server
python -m tool_loader serve
```

---

## Built-in Tools

Nine tools are bundled in `tool_loader.builtin_tools`.  
Call `seed_builtin_tools(registry)` to register them all automatically.

### File Tools (`file_tools`)

| Tool | Confirmation Required | Description |
|---|:---:|---|
| `search_files(pattern, directory=".")` | ❌ | Search files by glob pattern |
| `list_directory(directory=".", show_hidden=False)` | ❌ | List directory contents (name, type, size) |
| `read_file(file_path)` | ❌ | Read a file's text content |
| `write_file(file_path, content)` | ✅ | Create or overwrite a file |
| `delete_file(file_path)` | ✅ | Delete a file |

### Shell Tools (`shell_tools`)

| Tool | Confirmation Required | Description |
|---|:---:|---|
| `execute_file(file_path, args="")` | ✅ | Execute a script file (.py, .sh, .js, etc.) |
| `run_bash(command, timeout=30)` | ✅ | Run a bash command |

### HTTP Tools (`http_tools`)

| Tool | Confirmation Required | Description |
|---|:---:|---|
| `http_request(url, method="GET", headers="{}", body="", timeout=30)` | ❌ | Send an HTTP request (curl alternative) |

### System Tools (`system_tools`)

| Tool | Confirmation Required | Description |
|---|:---:|---|
| `get_system_info()` | ❌ | Return OS, CPU core count, and disk usage |

### User Confirmation Mechanism

Tools marked ✅ require **explicit user confirmation** before executing.

```
⚠️  About to perform the following action:
  Delete file: /home/user/important.txt
Continue? [y/N]:
```

- Executes only when the user types `y`; any other input cancels the operation.
- A LangChain agent receives the cancellation result and can handle it in its higher-level flow.
- In non-interactive environments (EOF), the operation is automatically cancelled.

### Seeding Built-in Tools

```python
from tool_loader import CryptoManager, Registry
from tool_loader.builtin_tools import BUILTIN_MODULE, seed_builtin_tools

crypto = CryptoManager(key=...)
registry = Registry(db_url="sqlite+aiosqlite:///tools.db", crypto=crypto)
await registry.init_db()

# Inserts only tools not already registered (idempotent)
inserted = await seed_builtin_tools(registry)

# Add the built-in module to the allowlist
loader = UniversalLoader(
    registry=registry,
    process_manager=process_manager,
    allowed_modules={BUILTIN_MODULE},
)
```

---

## Adding a Custom Python Tool

```python
# 1. Define a LangChain @tool function
from langchain_core.tools import tool

@tool
def my_tool(x: int) -> str:
    """My custom tool."""
    return str(x * 2)

# 2. Register it in the registry
from tool_loader.models import ToolSchema, ToolType

await registry.add_tool(ToolSchema(
    name="my_tool",
    type=ToolType.PYTHON,
    path_or_cmd="my_module:my_tool",  # "module:function" format
    description="Returns the input value doubled.",
))

# 3. Add the module to allowed_modules
loader = UniversalLoader(
    ...,
    allowed_modules={"my_module"},
)
```

## Adding an MCP Tool

```python
from tool_loader.models import ToolSchema, ToolType, TerminationPolicy

await registry.add_tool(ToolSchema(
    name="filesystem_mcp",
    type=ToolType.MCP,
    path_or_cmd="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    termination_policy=TerminationPolicy.PERSISTENT,
    description="Filesystem MCP server",
))
```

## config_server (Runtime Tool Management)

Running the embedded FastMCP server over stdio lets a connected LLM agent CRUD tools at runtime.

```bash
# Recommended: via CLI
python -m tool_loader serve

# Or run the subpackage directly
python -m tool_loader.config_server \
  --db-url sqlite+aiosqlite:///tools.db \
  --fernet-key <FERNET_KEY>
```

Exposed MCP tools: `list_tools`, `get_tool`, `add_tool`, `toggle_tool`, `delete_tool`

---

## Exception Handling

All custom exceptions can be imported from `tool_loader.exceptions`.

| Exception | Raised When |
|---|---|
| `ToolNotFoundError` | `delete_tool(id)` is called with a non-existent ID |
| `SystemToolError` | Attempting to modify or delete a tool where `is_system=True` |
| `DecryptionError` | `env_vars` decryption fails (e.g., key mismatch) |
| `ModuleNotAllowedError` | Attempting to load a module not in the `allowed_modules` whitelist |
| `ToolLoadError` | An individual tool fails to load during `aload_all(safe_mode=True)` |

```python
from tool_loader.exceptions import ToolNotFoundError, SystemToolError

try:
    await registry.delete_tool(tool_id)
except ToolNotFoundError:
    print("Tool not found.")
except SystemToolError:
    print("System tools cannot be deleted.")
```

> **Note**: Before v0.1, `delete_tool` silently ignored non-existent IDs.  
> It now raises `ToolNotFoundError`.

---

## Testing

```bash
pytest -v --asyncio-mode=auto
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TOOL_LOADER_FERNET_KEY` | (auto-generated) | Fernet encryption key (base64) |
| `TOOL_LOADER_DB_URL` | `sqlite+aiosqlite:///tools.db` | SQLAlchemy DB URL |
