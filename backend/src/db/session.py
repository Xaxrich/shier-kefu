"""异步 SQLite 会话与建表。"""

from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.settings import get_settings
from src.db.models import (  # noqa: F401
    Base,
    KbChunk,
    KbDocument,
    KbIngestJob,
    Message,
    QaPair,
    Ticket,
    User,
)


async def _seed_qa_pair() -> None:
    assert _async_session_maker is not None
    async with _async_session_maker() as session:
        r = await session.execute(select(QaPair).limit(1))
        if r.scalar_one_or_none() is not None:
            return
        session.add(
            QaPair(
                question_text="如何联系IT支持",
                answer_text="请通过内部工单系统提交申请，或拨打 IT 服务分机（见员工手册首页）。",
                question_embedding_json=None,
            )
        )
        await session.commit()

_engine = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def _ensure_engine() -> None:
    global _engine, _async_session_maker
    if _engine is not None:
        return
    settings = get_settings()
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
    )
    _async_session_maker = async_sessionmaker(_engine, expire_on_commit=False)


async def init_db() -> None:
    _ensure_engine()
    assert _engine is not None
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_demo_user()
    await _seed_qa_pair()


async def _seed_demo_user() -> None:
    from src.services.auth_service import hash_password

    assert _async_session_maker is not None
    async with _async_session_maker() as session:
        r = await session.execute(select(User).limit(1))
        if r.scalar_one_or_none() is not None:
            return
        session.add(
            User(
                username="demo",
                password_hash=hash_password("demo123"),
                role="both",
            )
        )
        await session.commit()


async def close_db() -> None:
    global _engine, _async_session_maker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _async_session_maker = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    _ensure_engine()
    assert _async_session_maker is not None
    async with _async_session_maker() as session:
        yield session
