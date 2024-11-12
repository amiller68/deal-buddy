import logging
from datetime import datetime, UTC
import io
from src.database.models import Om, OmStatus
from src.storage import StorageBucket
from src.utils import extract_text_from_pdf_stream
from src.llm.om import generate_summary

async def process_om(ctx, om_id: str):
    """Process an OM document"""
    logger = ctx['logger'].get_worker_logger()
    logger.info(f"Starting OM processing for om_id: {om_id}")
    try:
        async with ctx['database'].session() as session:
            om = await Om.read(om_id, session)
            if not om:
                logger.error(f"Om {om_id} not found")
                raise ValueError(f"Om {om_id} not found")
            
            # Update status to processing
            om.status = OmStatus.PROCESSING
            await session.commit()

            try:
                response = ctx['storage'].get_object(
                    bucket=StorageBucket.oms,
                    object_name=om.upload_id
                )
                file_content = response.data  # Use .data instead of .read() for MinIO
                
                pdf_text = extract_text_from_pdf_stream(io.BytesIO(file_content))
                summary = generate_summary(
                    anthropic_client=ctx['anthropic'],
                    pdf_text=pdf_text
                )

                # Update with success
                om.summary = summary
                om.status = OmStatus.PROCESSED
                om.processed_at = datetime.now(UTC)
                
            except Exception as e:
                om.status = OmStatus.FAILED
                raise
                
            finally:
                await session.commit()

    except Exception as e:
        logger.exception(f"Failed to process OM {om_id}")
        raise