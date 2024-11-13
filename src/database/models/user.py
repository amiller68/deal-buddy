from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime
from datetime import datetime
import uuid
from sqlalchemy.future import select

from src.logger import RequestSpan
from ..database import Base, DatabaseException


class User(Base):
    __tablename__ = "users"

    # Unique identifier
    id = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )

    # email
    email = Column(String, unique=True, nullable=False)

    # timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @staticmethod
    async def create(
        email: str, session: AsyncSession, span: RequestSpan | None = None
    ):
        try:
            user = User(email=email)
            session.add(user)
            await session.flush()
            return user
        except Exception as e:
            if span:
                span.error(f"database::models::User::create: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e

    @staticmethod
    async def read(id: str, session: AsyncSession, span: RequestSpan | None = None):
        try:
            result = await session.execute(select(User).filter_by(id=id))
            return result.scalars().first()
        except Exception as e:
            if span:
                span.error(f"database::models::User::read: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e

    @staticmethod
    async def read_by_email(
        email: str, session: AsyncSession, span: RequestSpan | None = None
    ):
        try:
            result = await session.execute(select(User).filter_by(email=email))
            return result.scalars().first()
        except Exception as e:
            if span:
                span.error(f"database::models::User::read_by_email: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e
