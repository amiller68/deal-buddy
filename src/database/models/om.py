from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, update, ForeignKey
from datetime import datetime, UTC
import uuid
from sqlalchemy.future import select
from typing import Dict, Any
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum

from src.logger import RequestSpan
from ..database import Base, DatabaseException


class OmStatus(str, Enum):
    # the om is uploaded but not yet processed
    UPLOADED = "uploaded"
    # the om is being processed by the worker -- marked by the worker
    PROCESSING = "processing"
    # the om is processed -- marked by the worker
    PROCESSED = "processed"
    # TODO: would be cool to have way to record why it failed
    # the om processing failed -- marked by the worker
    FAILED = "failed"


class Om(Base):
    __tablename__ = "oms"

    id = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )

    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    upload_id = Column(String, nullable=False)

    address = Column(String, nullable=True)

    title = Column(String, nullable=True)

    description = Column(String, nullable=True)

    summary = Column(String, nullable=True)

    status: Column[OmStatus] = Column(
        SQLAlchemyEnum(OmStatus), nullable=False, default=OmStatus.UPLOADED
    )

    # timestamps
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    @staticmethod
    async def create(
        user_id: str,
        upload_id: str,
        session: AsyncSession,
        span: RequestSpan | None = None,
    ):
        try:
            if span:
                span.debug(f"database::models::Om::create: {user_id} {upload_id}")
            om = Om(
                user_id=user_id,
                upload_id=upload_id,
            )
            session.add(om)
            await session.flush()
            return om
        except Exception as e:
            if span:
                span.error(f"database::models::Om::create: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e

    # TODO: ugly filter implementation
    @staticmethod
    async def read(id: str, session: AsyncSession, span: RequestSpan | None = None):
        if span:
            span.debug(f"database::models::Om::read: {id}")
        query = select(Om).filter_by(id=id)
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def update(
        id: str,
        update_data: Dict[str, Any],
        session: AsyncSession,
        span: RequestSpan | None = None,
    ):
        try:
            if span:
                span.debug(f"database::models::Om::update: {id}")
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

    @classmethod
    async def read_by_user_id(
        cls,
        user_id: str,
        session: AsyncSession,
        status: OmStatus | None = None,
        span: RequestSpan | None = None,
    ):
        if span:
            span.debug(f"database::models::Om::read_by_user_id: {user_id}")
        query = select(cls).where(cls.user_id == user_id)
        if status:
            query = query.where(cls.status == status)
        result = await session.execute(query)
        return result.scalars().all()
