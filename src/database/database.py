from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import asynccontextmanager
import asyncio
from enum import Enum as PyEnum

Base = declarative_base()

# NOTE: it is generally a good idea to make your database schema match your domain model
# At the moment all of our fields are the same, allowing us to interchange telebot types with our database types


class DatabaseExceptionType(PyEnum):
    conflict = "conflict"
    not_found = "not_found"
    invalid = "invalid"


class DatabaseException(Exception):
    def __init__(self, type: DatabaseExceptionType, message: str):
        self.message = message
        self.type = type

    def __str__(self):
        return f"{self.message}"

    @staticmethod
    def from_sqlalchemy_error(e):
        # TODO: better type checking here
        # If this is not an instance of a sqlalchemy error, just pass it through
        if not isinstance(e, Exception):
            return e
        if "FOREIGN KEY constraint failed" in str(e):
            return DatabaseException(DatabaseExceptionType.invalid, str(e))
        if "UNIQUE constraint failed" in str(e):
            return DatabaseException(DatabaseExceptionType.conflict, str(e))
        if "No row was found for one" in str(e):
            return DatabaseException(DatabaseExceptionType.not_found, str(e))
        if "CHECK constraint failed" in str(e):
            return DatabaseException(DatabaseExceptionType.invalid, str(e))
        # Otherwise just pass through the error
        return e


# Database Initialization and helpers


# Simple Synchronous Database for setting up the database
class SyncDatabase:
    def __init__(self, database_path):
        database_url = f"sqlite:///{database_path}"
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)


class AsyncDatabase:
    def __init__(self, database_path):
        self.database_path = database_path
        database_url = f"sqlite+aiosqlite:///{database_path}"

        # Configure engine with more conservative settings
        self.engine = create_async_engine(
            database_url,
            connect_args={
                "check_same_thread": False,
                "timeout": 30,
                "isolation_level": "IMMEDIATE",  # This helps prevent some locking issues
            },
            poolclass=StaticPool,  # StaticPool maintains a single connection
            echo=False,
        )

        self.AsyncSession = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def initialize(self):
        # Create tables first
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Try to set pragmas with retries
        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                async with self.engine.connect() as conn:
                    # Set pragmas one at a time
                    await conn.execute(text("PRAGMA busy_timeout = 5000"))
                    await conn.commit()

                    await conn.execute(text("PRAGMA journal_mode = WAL"))
                    await conn.commit()

                    await conn.execute(text("PRAGMA synchronous = NORMAL"))
                    await conn.commit()

                    break  # If we get here, everything worked
            except Exception:
                if attempt == max_retries - 1:  # Last attempt
                    raise  # Re-raise the exception if all retries failed
                await asyncio.sleep(retry_delay)

    @asynccontextmanager
    async def session(self):
        session = self.AsyncSession()
        try:
            yield session
        finally:
            await session.close()

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
