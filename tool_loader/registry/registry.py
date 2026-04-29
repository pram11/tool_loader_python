import json
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    Text,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from tool_loader.exceptions import SystemToolError, ToolNotFoundError
from tool_loader.models import ToolSchema
from tool_loader.security import CryptoManager


class _Base(DeclarativeBase):
    pass


class _ToolRow(_Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False, unique=True)
    type = Column(Text, nullable=False)
    path_or_cmd = Column(Text, nullable=False)
    args = Column(Text, nullable=False, default="[]")
    env_vars = Column(Text, nullable=False, default="{}")
    is_enabled = Column(Boolean, nullable=False, default=True)
    is_system = Column(Boolean, nullable=False, default=False)
    termination_policy = Column(Text, nullable=False, default="ON_DEMAND")
    description = Column(Text, nullable=False, default="")


class Registry:
    """Async SQLite-backed store for tool metadata.

    env_vars are automatically encrypted on write and decrypted on read.
    system tools (is_system=True) are protected from toggle operations.
    """

    def __init__(self, db_url: str, crypto: CryptoManager) -> None:
        self._engine = create_async_engine(db_url, echo=False)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )
        self._crypto = crypto

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init_db(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(_Base.metadata.create_all)

    async def close(self) -> None:
        await self._engine.dispose()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def add_tool(self, tool: ToolSchema) -> ToolSchema:
        encrypted = self._crypto.encrypt_env_vars(tool.env_vars)
        row = _ToolRow(
            name=tool.name,
            type=tool.type,
            path_or_cmd=tool.path_or_cmd,
            args=json.dumps(tool.args),
            env_vars=encrypted,
            is_enabled=tool.is_enabled,
            is_system=tool.is_system,
            termination_policy=tool.termination_policy,
            description=tool.description,
        )
        async with self._session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return self._row_to_schema(row)

    async def get_all_tools(self) -> List[ToolSchema]:
        async with self._session_factory() as session:
            result = await session.execute(select(_ToolRow))
            return [self._row_to_schema(r) for r in result.scalars()]

    async def get_enabled_tools(self) -> List[ToolSchema]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(_ToolRow).where(_ToolRow.is_enabled == True)  # noqa: E712
            )
            return [self._row_to_schema(r) for r in result.scalars()]

    async def get_tool_by_id(self, tool_id: int) -> Optional[ToolSchema]:
        async with self._session_factory() as session:
            row = await session.get(_ToolRow, tool_id)
            return self._row_to_schema(row) if row else None

    async def toggle_tool(self, tool_id: int, enabled: bool) -> None:
        async with self._session_factory() as session:
            row = await session.get(_ToolRow, tool_id)
            if row is None:
                return
            if row.is_system:
                raise SystemToolError(
                    f"Cannot toggle system tool '{row.name}' (id={tool_id})."
                )
            await session.execute(
                update(_ToolRow)
                .where(_ToolRow.id == tool_id)
                .values(is_enabled=enabled)
            )
            await session.commit()

    async def delete_tool(self, tool_id: int) -> None:
        async with self._session_factory() as session:
            row = await session.get(_ToolRow, tool_id)
            if row is None:
                raise ToolNotFoundError(f"Tool id={tool_id} not found.")
            if row.is_system:
                raise SystemToolError(
                    f"Cannot delete system tool '{row.name}' (id={tool_id})."
                )
            await session.delete(row)
            await session.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _row_to_schema(self, row: _ToolRow) -> ToolSchema:
        decrypted = self._crypto.decrypt_env_vars(row.env_vars)
        return ToolSchema(
            id=row.id,
            name=row.name,
            type=row.type,
            path_or_cmd=row.path_or_cmd,
            args=json.loads(row.args),
            env_vars=decrypted,
            is_enabled=row.is_enabled,
            is_system=row.is_system,
            termination_policy=row.termination_policy,
            description=row.description,
        )
