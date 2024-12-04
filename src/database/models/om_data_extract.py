from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, update, ForeignKey, JSON
from datetime import datetime, UTC, date
import uuid
from sqlalchemy.future import select
from typing import Dict, Any, Optional
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.types import TypeDecorator, JSON
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import List

from src.logger import RequestSpan
from ..database import Base, DatabaseException

class UnitType(str, Enum):
    OFFICE = "office"
    INDUSTRIAL = "industrial"
    RETAIL = "retail"
    COMMERCIAL = "commercial"
    ONE_BR = "1BR"
    TWO_BR = "2BR"
    THREE_BR = "3BR"
    FOUR_BR = "4BR"
    FIVE_BR = "5BR"

class OmExtractionStatus(str, Enum):
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

class ExtractionStatusWithError(BaseModel):
    status: OmExtractionStatus
    error_message: Optional[str] = None

class PydanticType(TypeDecorator):
    """Convert Pydantic model to and from JSON for SQLAlchemy"""
    impl = JSON
    
    def __init__(self, pydantic_type):
        super().__init__()
        self.pydantic_type = pydantic_type

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, list):
                return [item.model_dump() for item in value]
            return value.model_dump()
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            if isinstance(self.pydantic_type, list):
                model_type = self.pydantic_type[0]
                return [model_type.model_validate(item) for item in value]
            return self.pydantic_type.model_validate(value)
        return None


class RentRoll(BaseModel):
    unit: str
    unit_type: UnitType
    rent_stabilized: Optional[bool] = None
    square_feet: int
    lease_expiration: Optional[date] = None
    monthly_inplace_rent: Optional[int] = None
    annual_inplace_rent: Optional[int] = None
    monthly_projected_rent: Optional[int] = None
    annual_projected_rent: Optional[int] = None

    @field_validator('lease_expiration', mode='before')
    @classmethod
    def parse_date(cls, value: Optional[str]) -> Optional[date]:
        """Convert string dates to date objects and validate format"""
        if not value:
            return None
            
        if isinstance(value, date):
            return value
            
        try:
            # Handle different date formats the LLM might return
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d'):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Date {value} doesn't match any expected format")
        except Exception as e:
            raise ValueError(f"Invalid date format: {value}. Use YYYY-MM-DD") from e


class Expenses(BaseModel):
    in_place_income: int
    in_place_expenses: Dict[str, int]
    projected_income: int
    projected_expenses: Dict[str, int]


class OmDataExtract(Base):
    __tablename__ = "om_data_extracts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    om_id = Column(String, ForeignKey("oms.id"), nullable=False)
    status = Column(PydanticType(ExtractionStatusWithError), nullable=False, 
                   default=lambda: ExtractionStatusWithError(status=OmExtractionStatus.PROCESSING))

    # Pydantic models as column types
    rent_roll = Column(PydanticType(List[RentRoll]), nullable=True)
    expenses = Column(PydanticType(Expenses), nullable=True)

    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    @staticmethod
    async def create_with_data(
        om_id: str,
        analysis_data: Dict[str, Any],
        session: AsyncSession,
        span: RequestSpan | None = None,
    ) -> "OmDataExtract":
        try:
            if span:
                span.debug(f"database::models::OmExtract::create_with_data: {om_id}")
            
            # The data will automatically be converted to/from Pydantic models
            om = OmDataExtract(
                om_id=om_id,
                rent_roll=analysis_data.get("rent_roll"),
                expenses=analysis_data.get("expenses"),
                status=OmExtractionStatus.PROCESSED
            )
            
            session.add(om)
            await session.flush()
            return om
            
        except Exception as e:
            if span:
                span.error(f"database::models::OmExtract::create_with_data: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e

    @staticmethod
    async def read(id: str, session: AsyncSession, span: RequestSpan | None = None) -> Optional["OmDataExtract"]:
        if span:
            span.debug(f"database::models::OmDataExtract::read: {id}")
        query = select(OmDataExtract).filter_by(id=id)
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def read_by_om_id(
        om_id: str,
        session: AsyncSession,
        span: RequestSpan | None = None,
    ) -> Optional["OmDataExtract"]:
        if span:
            span.debug(f"database::models::OmDataExtract::read_by_om_id: {om_id}")
        query = select(OmDataExtract).filter_by(om_id=om_id)
        result = await session.execute(query)
        return result.scalars().first()

    @staticmethod
    async def update(
        id: str,
        update_data: Dict[str, Any],
        session: AsyncSession,
        span: RequestSpan | None = None,
    ) -> "OmDataExtract":
        try:
            if span:
                span.debug(f"database::models::OmExtract::update: {id}")
            
            result = await session.execute(select(OmDataExtract).filter_by(id=id))
            om = result.scalars().first()
            if not om:
                raise ValueError(f"OmExtract with id {id} not found")

            stmt = update(OmDataExtract).where(OmDataExtract.id == id).values(**update_data).returning(OmDataExtract)
            result = await session.execute(stmt)
            updated_om = result.scalars().first()
            if not updated_om:
                raise ValueError(f"OmDataExtract with id {id} not found")
            
            await session.commit()
            return updated_om
            
        except Exception as e:
            if span:
                span.error(f"database::models::OmExtract::update: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e
