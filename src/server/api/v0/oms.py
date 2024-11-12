from fastapi import APIRouter, Depends, HTTPException
from fastapi import (
    Depends,
    UploadFile,
    File,
)
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import io

from src.database.models import OmStatus, User, Om
from src.logger import RequestSpan
from src.storage import Storage, StorageBucket
from src.task_manager import TaskManager, TaskPriority
from ...deps import require_logged_in_user, span, async_db, storage, task_manager

router = APIRouter()

@router.post("")
async def create_om(
    file: UploadFile = File(...),
    user: User = Depends(require_logged_in_user),
    span: RequestSpan = Depends(span),
    db: AsyncSession = Depends(async_db),
    storage: Storage = Depends(storage),
    task_manager: TaskManager = Depends(task_manager),
):
    span.info(f"handling create_om: user_id={user.id}")
    try:
        # Validate file
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=422, detail="Only PDF files are allowed")
        
        # Read file
        try:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=422, detail="Empty file uploaded")
        except Exception as e:
            span.error(f"File read error: {str(e)}")
            raise HTTPException(status_code=422, detail="Error reading uploaded file")

        # Upload to storage
        upload_id = storage.put_object(
            stream=io.BytesIO(content),
            stream_len=len(content),
            bucket=StorageBucket.oms,
        )

        # Create initial Om record
        om = await Om.create(
            user_id=user.id,
            upload_id=upload_id,
            title="Pending Processing",  # Placeholder
            description="Processing...",  # Placeholder
            summary="",  # Will be filled by background task
            session=db,
            span=span,
        )

        await db.commit()

        print(f"om id: {om.id}")

        # Trigger background processing
        task_result = await task_manager.process_om(
            om_id=om.id,
        )

        return {
            "message": "Om created and processing started", 
            "om_id": om.id,
            "task_id": task_result.job_id
        }
        
    except Exception as e:
        span.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


class OmResponse(BaseModel):
    id: str
    user_id: str
    upload_id: str
    status: OmStatus


@router.get("")
async def get_oms(
    user: User = Depends(require_logged_in_user),
    span: RequestSpan = Depends(span),
    db: AsyncSession = Depends(async_db),
):
    try:
        oms = await Om.read_by_user_id(user_id=user.id, session=db, span=span)
        return [
            OmResponse(
                id=om.id,
                user_id=om.user_id,
                upload_id=om.upload_id,
            )
            for om in oms
        ]
    except Exception as e:
        span.error(f"Error fetching OMs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch OMs")
