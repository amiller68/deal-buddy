from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime, UTC
import uuid
from sqlalchemy.future import select
from typing import Dict, Any, List
import json

from src.logger import RequestSpan
from src.storage import StorageBucket
from ..database import Base, DatabaseException

class OmTable(Base):
    __tablename__ = "om_tables"

    id = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )

    om_id = Column(String, ForeignKey("oms.id"), nullable=False)
    
    # The type of table (any string identifier)
    type = Column(String, nullable=False)
    
    # The storage location of the table data in minio
    storage_object_id = Column(String, nullable=False)

    # timestamps
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    @staticmethod
    async def create_many(
        om_id: str,
        tables: Dict[str, List[Dict[str, Any]]],
        storage: StorageBucket,
        session: AsyncSession,
        span: RequestSpan | None = None,
    ) -> List["OmTable"]:
        """Create table entries and store data in minio"""
        try:
            if span:
                span.debug(f"database::models::OmTable::create_tables: {om_id}")
            
            created_tables = []
            
            for table_type, table_data in tables.items():
                # Store table data in minio
                storage_object_id = storage.put_object(
                    bucket=StorageBucket.OM_TABLES,
                    data=json.dumps(table_data).encode(),
                    content_type="application/json"
                )
                
                # Create table record
                table = OmTable(
                    om_id=om_id,
                    type=table_type,
                    storage_object_id=storage_object_id,
                )
                session.add(table)
                created_tables.append(table)
            
            await session.flush()
            return created_tables
            
        except Exception as e:
            if span:
                span.error(f"database::models::OmTable::create_tables: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e
