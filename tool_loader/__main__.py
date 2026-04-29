"""CLI entry point: python -m tool_loader <subcommand> [options]

Subcommands:
  keygen   Generate a new Fernet encryption key
  list     List registered tools
  add      Register a new tool
  delete   Remove a tool by ID
  toggle   Enable or disable a tool by ID
  load     Load all enabled tools and report results
  serve    Launch the config MCP server (stdio transport)

Global options (all DB subcommands):
  --db-url URL        SQLAlchemy async DB URL  [env: TOOL_LOADER_DB_URL]
  --fernet-key KEY    Base64 Fernet key        [env: TOOL_LOADER_FERNET_KEY]
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Set

from tool_loader.builtin_tools import BUILTIN_MODULE, seed_builtin_tools
from tool_loader.core.loader import UniversalLoader
from tool_loader.core.process_manager import ProcessManager
from tool_loader.exceptions import SystemToolError, ToolNotFoundError
from tool_loader.models import TerminationPolicy, ToolSchema, ToolType
from tool_loader.registry import Registry
from tool_loader.security import CryptoManager


# ──────────────────────────────────────────────────────────────────────────────
# Argument parser
# ──────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m tool_loader",
        description="SQLite-backed async tool loader for LangChain agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--db-url",
        default=os.environ.get("TOOL_LOADER_DB_URL", "sqlite+aiosqlite:///tools.db"),
        metavar="URL",
        help="SQLAlchemy async DB URL (env: TOOL_LOADER_DB_URL)",
    )
    p.add_argument(
        "--fernet-key",
        default=os.environ.get("TOOL_LOADER_FERNET_KEY"),
        metavar="KEY",
        help="Base64 Fernet key (env: TOOL_LOADER_FERNET_KEY)",
    )

    sub = p.add_subparsers(dest="command", metavar="SUBCOMMAND")
    sub.required = True

    # keygen ──────────────────────────────────────────────────────────────────
    sub.add_parser("keygen", help="Generate a new Fernet encryption key")

    # list ────────────────────────────────────────────────────────────────────
    p_list = sub.add_parser("list", help="List registered tools")
    p_list.add_argument(
        "--enabled-only",
        action="store_true",
        help="Show only enabled tools",
    )

    # add ─────────────────────────────────────────────────────────────────────
    p_add = sub.add_parser("add", help="Register a new tool")
    p_add.add_argument("--name", required=True, help="Unique tool name")
    p_add.add_argument(
        "--type", required=True, choices=["mcp", "python"], help="Tool type"
    )
    p_add.add_argument(
        "--path",
        required=True,
        dest="path_or_cmd",
        metavar="PATH_OR_CMD",
        help="Executable path (mcp) or 'module:callable' (python)",
    )
    p_add.add_argument(
        "--args",
        default="[]",
        metavar="JSON",
        help='JSON array of CLI arguments, e.g. \'["-y","@scope/pkg"]\'',
    )
    p_add.add_argument(
        "--env",
        default="{}",
        metavar="JSON",
        help='JSON object of environment variables, e.g. \'{"KEY":"val"}\'',
    )
    p_add.add_argument(
        "--policy",
        default="ON_DEMAND",
        choices=["ON_DEMAND", "PERSISTENT"],
        help="Process termination policy",
    )
    p_add.add_argument("--description", default="", help="Human-readable description")

    # delete ──────────────────────────────────────────────────────────────────
    p_del = sub.add_parser("delete", help="Remove a tool by ID")
    p_del.add_argument("id", type=int, metavar="TOOL_ID")

    # toggle ──────────────────────────────────────────────────────────────────
    p_tog = sub.add_parser("toggle", help="Enable or disable a tool by ID")
    p_tog.add_argument("id", type=int, metavar="TOOL_ID")
    tog_group = p_tog.add_mutually_exclusive_group(required=True)
    tog_group.add_argument("--enable", dest="enabled", action="store_true")
    tog_group.add_argument("--disable", dest="enabled", action="store_false")

    # load ────────────────────────────────────────────────────────────────────
    p_load = sub.add_parser("load", help="Load all enabled tools and report results")
    p_load.add_argument(
        "--allowed-modules",
        default="",
        metavar="MODULES",
        help="Comma-separated additional importable module prefixes",
    )
    p_load.add_argument(
        "--seed-builtins",
        action="store_true",
        help="Auto-register built-in tools before loading",
    )

    # serve ───────────────────────────────────────────────────────────────────
    sub.add_parser("serve", help="Launch the config MCP server (stdio transport)")

    return p


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_crypto(args: argparse.Namespace) -> CryptoManager:
    if args.fernet_key:
        return CryptoManager(key=args.fernet_key.encode())
    key = CryptoManager.generate_key()
    print(
        f"[warn] No --fernet-key / TOOL_LOADER_FERNET_KEY found.\n"
        f"       Generated a temporary key (data will be unreadable next run):\n"
        f"       {key.decode()}\n",
        file=sys.stderr,
    )
    return CryptoManager(key=key)


async def _open_registry(args: argparse.Namespace) -> Registry:
    reg = Registry(db_url=args.db_url, crypto=_make_crypto(args))
    await reg.init_db()
    return reg


# ──────────────────────────────────────────────────────────────────────────────
# Subcommand handlers
# ──────────────────────────────────────────────────────────────────────────────

def cmd_keygen(_args: argparse.Namespace) -> None:
    print(CryptoManager.generate_key().decode())


async def cmd_list(args: argparse.Namespace) -> None:
    reg = await _open_registry(args)
    try:
        tools = (
            await reg.get_enabled_tools()
            if args.enabled_only
            else await reg.get_all_tools()
        )
    finally:
        await reg.close()

    if not tools:
        print("(no tools registered)")
        return

    id_w, name_w, type_w, path_w = 4, 22, 8, 32
    header = (
        f"{'ID':<{id_w}}  {'NAME':<{name_w}}  {'TYPE':<{type_w}}  "
        f"{'PATH / CMD':<{path_w}}  ENABLED"
    )
    print(header)
    print("-" * len(header))
    for t in tools:
        print(
            f"{t.id!s:<{id_w}}  {t.name:<{name_w}}  {t.type:<{type_w}}  "
            f"{t.path_or_cmd:<{path_w}}  {'yes' if t.is_enabled else 'no'}"
        )


async def cmd_add(args: argparse.Namespace) -> None:
    try:
        tool_args = json.loads(args.args)
        tool_env = json.loads(args.env)
    except json.JSONDecodeError as exc:
        print(f"[error] Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    tool = ToolSchema(
        name=args.name,
        type=ToolType(args.type),
        path_or_cmd=args.path_or_cmd,
        args=tool_args,
        env_vars=tool_env,
        termination_policy=TerminationPolicy(args.policy),
        description=args.description,
    )

    reg = await _open_registry(args)
    try:
        added = await reg.add_tool(tool)
    finally:
        await reg.close()

    print(f"[ok] Added '{added.name}' (id={added.id})")


async def cmd_delete(args: argparse.Namespace) -> None:
    reg = await _open_registry(args)
    try:
        await reg.delete_tool(args.id)
    except (ToolNotFoundError, SystemToolError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        await reg.close()

    print(f"[ok] Deleted tool id={args.id}")


async def cmd_toggle(args: argparse.Namespace) -> None:
    reg = await _open_registry(args)
    try:
        tool = await reg.get_tool_by_id(args.id)
        if tool is None:
            print(f"[error] Tool id={args.id} not found.", file=sys.stderr)
            sys.exit(1)
        await reg.toggle_tool(args.id, args.enabled)
    except SystemToolError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        await reg.close()

    state = "enabled" if args.enabled else "disabled"
    print(f"[ok] Tool id={args.id} is now {state}")


async def cmd_load(args: argparse.Namespace) -> None:
    reg = await _open_registry(args)
    pm = ProcessManager()

    allowed: Set[str] = {BUILTIN_MODULE}
    if args.allowed_modules:
        allowed |= {m.strip() for m in args.allowed_modules.split(",") if m.strip()}

    loader = UniversalLoader(registry=reg, process_manager=pm, allowed_modules=allowed)

    try:
        if args.seed_builtins:
            n = await seed_builtin_tools(reg)
            if n:
                print(f"[init] Seeded {n} built-in tool(s).")

        result = await loader.aload_all(safe_mode=True, return_failures=True)
    finally:
        await pm.close_all()
        await reg.close()

    print(f"Loaded {len(result.tools)} tool(s):")
    for t in result.tools:
        label = getattr(t, "name", None) or getattr(t, "__name__", repr(t))
        print(f"  • {label}")

    if result.failures:
        print(f"\n{len(result.failures)} failure(s):")
        for f in result.failures:
            print(f"  • [{f.tool_name}] {f.reason}")


def cmd_serve(args: argparse.Namespace) -> None:
    if not args.fernet_key:
        print(
            "[error] --fernet-key / TOOL_LOADER_FERNET_KEY is required for serve.",
            file=sys.stderr,
        )
        sys.exit(1)

    from tool_loader.config_server.server import _run  # noqa: PLC2701

    asyncio.run(_run(args.db_url, args.fernet_key))


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

_ASYNC_COMMANDS = {
    "list": cmd_list,
    "add": cmd_add,
    "delete": cmd_delete,
    "toggle": cmd_toggle,
    "load": cmd_load,
}


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "keygen":
        cmd_keygen(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command in _ASYNC_COMMANDS:
        asyncio.run(_ASYNC_COMMANDS[args.command](args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
