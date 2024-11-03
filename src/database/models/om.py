from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, update, ForeignKey
from datetime import datetime
import uuid
from sqlalchemy.future import select
from typing import Dict, Any
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum


from src.logger import RequestSpan
from ..database import Base, DatabaseException

class OmStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

class Om(Base):
    __tablename__ = "oms"

    id = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )

    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    upload_id = Column(String, nullable=False)

    title = Column(String, nullable=False)

    description = Column(String, nullable=True)

    summary = Column(String, nullable=True)

    status = Column(SQLAlchemyEnum(OmStatus), nullable=False, default=OmStatus.UPLOADING)
    processed_at = Column(DateTime)

    # timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    async def create(
        user_id: str,
        upload_id: str,
        title: str,
        description: str,
        summary: str,
        session: AsyncSession,
        span: RequestSpan | None = None,
    ):
        try:
            om = Om(
                user_id=user_id,
                upload_id=upload_id,
                title=title,
                description=description,
                summary=summary,
            )
            session.add(om)
            await session.flush()
            return om
        except Exception as e:
            if span:
                span.error(f"database::models::Om::create: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e

    @staticmethod
    async def read(id: str, session: AsyncSession, span: RequestSpan | None = None):
        result = await session.execute(select(Om).filter_by(id=id))
        return result.scalars().first()

    @staticmethod
    async def update(
        id: str,
        update_data: Dict[str, Any],
        session: AsyncSession,
        span: RequestSpan | None = None,
    ):
        try:
            # First, check if the Om exists
            result = await session.execute(select(Om).filter_by(id=id))
            om = result.scalars().first()
            if not om:
                raise ValueError(f"Om with id {id} not found")

            # Update the Om
            stmt = update(Om).where(Om.id == id).values(**update_data).returning(Om)
            result = await session.execute(stmt)
            updated_om = result.scalars().first()
            if not updated_om:
                raise ValueError(f"Om with id {id} not found")
            await session.commit()
            return updated_om
        except Exception as e:
            if span:
                span.error(f"database::models::Om::update: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e

    @staticmethod
    async def update_summary(
        id: str, summary: str, session: AsyncSession, span: RequestSpan | None = None
    ):
        return await Om.update(id, {"summary": summary}, session, span)

    @classmethod
    async def read_by_user_id(
        cls, user_id: str, session: AsyncSession, span: RequestSpan
    ):
        query = select(cls).where(cls.user_id == user_id)
        result = await session.execute(query)
        return result.scalars().all()
