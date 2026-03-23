"""
Database setup and session management.
Supports both sync (SQLite) and async (PostgreSQL) modes.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator, AsyncGenerator
import os

# Get database URL from environment or use SQLite default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./empirebox.db")

# Base class for models
Base = declarative_base()

# Check if using async database (PostgreSQL)
is_async = DATABASE_URL.startswith("postgresql+asyncpg")

if is_async:
    # Async engine for PostgreSQL
    engine = create_async_engine(
        DATABASE_URL,
        echo=True,  # Set to False in production
        future=True
    )

    # Async session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        """
        Dependency for getting async database sessions.
        Yields a session and ensures it's closed after use.
        """
        async with async_session_maker() as session:
            try:
                yield session
            finally:
                await session.close()

    async def init_db():
        """Initialize database tables. For development only."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

else:
    # Sync engine for SQLite
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    )

    # Sync session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_db() -> Generator:
        """
        Dependency for getting sync database sessions.
        Yields a session and ensures it's closed after use.
        """
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def init_db():
        """Initialize database tables. For development only."""
        Base.metadata.create_all(bind=engine)

    # --- Async SQLite session for routers that need async ORM (chat_backup) ---
    try:
        import aiosqlite  # noqa: F401
        _ASYNC_SQLITE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

        _async_engine = create_async_engine(
            _ASYNC_SQLITE_URL,
            echo=False,
            future=True,
        )

        _async_session_maker = async_sessionmaker(
            _async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
            """
            Async dependency for routers that use async SQLAlchemy ORM
            (e.g. chat_backup). Separate from the sync get_db used by
            most routers.
            """
            async with _async_session_maker() as session:
                try:
                    yield session
                finally:
                    await session.close()

    except ImportError:
        # aiosqlite not installed — chat_backup router will fail at runtime
        async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
            raise RuntimeError(
                "aiosqlite is required for async SQLite sessions. "
                "Install it with: pip install aiosqlite"
            )
            yield  # make it a generator  # type: ignore
