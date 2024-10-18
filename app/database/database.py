from sqlalchemy import (
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
        database_url = f"sqlite+aiosqlite:///{database_path}"
        self.engine = create_async_engine(database_url)
        self.AsyncSession = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        # If this is an in-memory database, we need to create the tables
        if database_path == ":memory:":
            asyncio.run(self.create_tables())

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
