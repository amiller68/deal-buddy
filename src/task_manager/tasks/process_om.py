from src.database.models import Om, OmStatus
from datetime import datetime
import io
import asyncio

from src.database.models import Om, OmStatus
from src.storage import StorageBucket
from src.utils import extract_text_from_pdf_stream
from src.llm.om import generate_summary

from . import task

@task(name="process_om")
def process_om(self, om_id: str):
    try:
        state = self.request.app_state
        state.logger.info(f"Starting OM processing for om_id: {om_id}")

        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def process():
            async with state.database.session() as session:
                om = await Om.get_by_id(om_id, session)
                if not om:
                    raise ValueError(f"Om {om_id} not found")
                
                # Update status to processing
                om.status = OmStatus.PROCESSING
                await session.commit()

                try:
                    file_content = await state.storage.get_object(
                        bucket=StorageBucket.oms,
                        object_id=om.upload_id
                    )
                    
                    pdf_text = await extract_text_from_pdf_stream(io.BytesIO(file_content))
                    summary = await generate_summary(
                        anthropic_client=state.anthropic_client,
                        pdf_text=pdf_text
                    )

                    # Update with success
                    om.summary = summary
                    om.status = OmStatus.PROCESSED
                    om.processed_at = datetime.utcnow()
                    
                except Exception as e:
                    om.status = OmStatus.FAILED
                    raise
                    
                finally:
                    await session.commit()

        # Run the async process in the event loop
        try:
            loop.run_until_complete(process())
            state.logger.info(f"Successfully processed OM {om_id}")
        finally:
            loop.close()
            
    except Exception as e:
        state.logger.error(f"Failed to process OM {om_id}: {str(e)}")
        raise self.retry(exc=e)