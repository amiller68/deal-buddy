from fastapi import APIRouter, Depends, HTTPException
from fastapi import (
    Depends,
    UploadFile,
    File,
)
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import io

from anthropic import Anthropic

from app.database.models import User, Om
from app.logger import RequestSpan
from app.storage import Storage, StorageBucket
from app.utils import extract_text_from_pdf_stream
from app.llm.om import generate_summary

from ...deps import require_logged_in_user, span, async_db, storage, anthropic_client

router = APIRouter()

@router.post("")
async def create_om(
    file: UploadFile = File(...),
    user: User = Depends(require_logged_in_user),
    span: RequestSpan = Depends(span),
    db: AsyncSession = Depends(async_db),
    storage: Storage = Depends(storage),
    anthropic_client: Anthropic = Depends(anthropic_client),
):
    span.info(f"handling create_om: user_id={user.id}")
    try:
        # Add file validation
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=422, detail="Only PDF files are allowed")
        
        span.info("before file.read")
        # Read the file content with error handling
        try:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=422, detail="Empty file uploaded")
        except Exception as e:
            span.error(f"File read error: {str(e)}")
            raise HTTPException(status_code=422, detail="Error reading uploaded file")

        span.info("before file_size")
        file_size = len(content)

        print(file_size)

        # Upload to MinIO
        upload_id = storage.put_object(
            stream=io.BytesIO(content),
            stream_len=file_size,
            bucket=StorageBucket.oms,
        )

        print(upload_id)

        # Extract text and generate summary
        pdf_text = extract_text_from_pdf_stream(io.BytesIO(content))



        print(pdf_text)
        summary = await generate_summary(
            anthropic_client=anthropic_client,
            pdf_text=pdf_text
        )

        print(summary)

        # Create Om record
        om = await Om.create(
            user_id=user.id,
            upload_id=upload_id,
            title="Bachelor Pad",
            description="A sick bachelor pad -- just 2 mil down!",
            summary=summary,
            session=db,
            span=span,
        )

        return {"message": "Om uploaded successfully", "om_id": om.id}
    except Exception as e:
        span.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


class OmResponse(BaseModel):
    id: str
    user_id: str
    upload_id: str


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
