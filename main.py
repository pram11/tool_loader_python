"""Integration entry point for tool_loader.

Demonstrates the full initialization sequence:
  CryptoManager → Registry → ProcessManager → UniversalLoader → LangChain agent
"""

import asyncio
import os

from tool_loader import (
    CryptoManager,
    LoadResult,
    ProcessManager,
    Registry,
    ToolSchema,
    ToolType,
    UniversalLoader,
)
from tool_loader.builtin_tools import BUILTIN_MODULE, seed_builtin_tools


async def security_validator(tool_name: str) -> bool:
    """Prompt the operator before toggling a non-system tool."""
    answer = input(f"[security] Enable/disable '{tool_name}'? (y/n): ").strip().lower()
    return answer == "y"


async def main() -> None:
    # 1. CryptoManager — key from environment
    fernet_key = os.environ.get("TOOL_LOADER_FERNET_KEY")
    if not fernet_key:
        new_key = CryptoManager.generate_key()
        print(f"[init] No TOOL_LOADER_FERNET_KEY set. Generated key (save this!):\n  {new_key.decode()}\n")
        crypto = CryptoManager(key=new_key)
    else:
        crypto = CryptoManager(key=fernet_key.encode())

    # 2. Registry
    db_url = os.environ.get("TOOL_LOADER_DB_URL", "sqlite+aiosqlite:///tools.db")
    registry = Registry(db_url=db_url, crypto=crypto)
    await registry.init_db()

    # 3. ProcessManager
    process_manager = ProcessManager(idle_timeout=300.0)

    # 4. UniversalLoader with module whitelist
    allowed_modules = {"math", "os.path", BUILTIN_MODULE}
    loader = UniversalLoader(
        registry=registry,
        process_manager=process_manager,
        allowed_modules=allowed_modules,
    )

    try:
        # Seed built-in tools (idempotent — skips already-registered names)
        inserted = await seed_builtin_tools(registry)
        if inserted:
            print(f"[init] Seeded {inserted} built-in tool(s).")

        # Seed a sample python tool if the registry has no user tools
        existing_names = {t.name for t in await registry.get_all_tools()}
        if "math_gcd" not in existing_names:
            await registry.add_tool(ToolSchema(
                name="math_gcd",
                type=ToolType.PYTHON,
                path_or_cmd="math:gcd",
                description="Greatest common divisor via math.gcd",
            ))
            print("[init] Seeded sample tool 'math_gcd'.")

        # 5. Load all enabled tools
        result: LoadResult = await loader.aload_all(
            safe_mode=True,
            return_failures=True,
        )

        print(f"\n✅  Loaded {len(result.tools)} tool(s):")
        for t in result.tools:
            print(f"    • {getattr(t, '__name__', repr(t))}")

        if result.failures:
            print(f"\n⚠️  {len(result.failures)} tool(s) failed to load:")
            for f in result.failures:
                print(f"    • [{f.tool_name}] {f.reason}")

    finally:
        # 6. Graceful shutdown
        await process_manager.close_all()
        await registry.close()
        print("\n[shutdown] All processes and DB connections closed.")


if __name__ == "__main__":
    asyncio.run(main())
