from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import (
    Depends,
    UploadFile,
    File,
)
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import io
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.database.models import OmStatus, User, Om
from src.logger import RequestSpan
from src.storage import Storage, StorageBucket
from src.task_manager import TaskManager, TaskPriority
from ...deps import require_logged_in_user, span, async_db, storage, task_manager

router = APIRouter()

templates = Jinja2Templates(directory="templates")


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
        if not file.filename or not file.filename.lower().endswith(".pdf"):
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
            session=db,
            span=span,
        )

        await db.commit()

        # TODO: i should probably do something with the task_result
        # Trigger background processing
        _task_result = await task_manager.process_om(
            om_id=om.id,
        )

        return {
            "om_id": om.id,
            "status": om.status,
        }

    except Exception as e:
        span.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


class OmResponse(BaseModel):
    id: str
    user_id: str
    status: OmStatus
    title: str | None = None
    description: str | None = None
    summary: str | None = None


@router.get("")
async def get_oms(
    request: Request,
    user: User = Depends(require_logged_in_user),
    span: RequestSpan = Depends(span),
    db: AsyncSession = Depends(async_db),
):
    try:
        oms = await Om.read_by_user_id(
            user_id=user.id, session=db, span=span, status=OmStatus.PROCESSED
        )
        om_responses = [
            OmResponse(
                id=om.id,
                user_id=om.user_id,
                status=om.status,
                title=om.title,
                description=om.description,
            )
            for om in oms
        ]

        # Check if request is from HTMX
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "app/components/oms.html", {"request": request, "oms": om_responses}
            )

        # Return JSON for regular API requests
        return om_responses

    except Exception as e:
        span.error(f"Error fetching OMs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch OMs")


@router.get("/{om_id}")
async def get_om(
    om_id: str,
    request: Request,
    poll: bool = False,
    user: User = Depends(require_logged_in_user),
    span: RequestSpan = Depends(span),
    db: AsyncSession = Depends(async_db),
):
    om = await Om.read(id=om_id, session=db, span=span)
    if not om:
        raise HTTPException(status_code=404, detail="OM not found")
    if om.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="You are not authorized to access this OM"
        )

    # Convert to response model
    om_response = OmResponse(
        id=om.id,
        user_id=om.user_id,
        status=om.status,
        title=om.title,
        description=om.description,
        summary=om.summary,
    )

    # Handle HTMX polling requests
    if request.headers.get("HX-Request") and poll:
        if om.status != OmStatus.PROCESSED:
            return templates.TemplateResponse(
                "app/components/om.html", {"request": request, "om": om_response}
            )
        # If processed, return the content component
        return templates.TemplateResponse(
            "app/components/om.html", {"request": request, "om": om_response}
        )

    # For full page requests, render the page template
    return templates.TemplateResponse(
        "app/index.html",
        {
            "request": request,
            "initial_content": "app/content/om.html",
            "om": om_response,
        },
    )
