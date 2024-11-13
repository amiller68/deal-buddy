import logging
from datetime import datetime, UTC
import io
# used by dependency
import json
from arq import Retry

from src.database.models import Om, OmStatus
from src.storage import StorageBucket
from src.utils import extract_text_from_pdf_stream
from src.llm.om import generate_summary

async def process_om(ctx, om_id: str, max_tries: int = 5):
    """Process an OM document"""
    storage = ctx['storage']
    anthropic = ctx['anthropic']
    redis = ctx['redis']
    database = ctx['database']
    job_try = ctx['job_try']
    logger = ctx['logger'].get_worker_logger(name='process_om', attempt=job_try)

    logger.info(f"processing  om -- {om_id}")
    try:
        async with database.session() as session:
            # read and check status
            # arq tasks are pessimistic, so they may retry even if they succeed
            # so we need to check if the om is already processed
            om = await Om.read(om_id, session)
            if not om:
                logger.error(f"om -- {om_id} not found")
                raise ValueError(f"om -- {om_id} not found")
            if om.status == OmStatus.PROCESSED:
                logger.info(f"om -- {om_id} already processed")
                return
            
            # Update status to processing and publish status update
            try:
                om.status = OmStatus.PROCESSING
                # Publish status update
                await redis.publish(
                    'process_om_status',
                    json.dumps({
                        'om_id': om_id,
                        'status': OmStatus.PROCESSING
                    })
                )
            except Exception as e:
                logger.exception(f"failed to publish status update for om -- {om_id} | {e}")
                # TODO: not sure if we should do this here or not
                if job_try == max_tries:
                    om.status = OmStatus.FAILED
                raise
            finally:
                await session.commit()

            # process the om
            try:
                # read the om file
                response = storage.get_object(
                    bucket=StorageBucket.oms,
                    object_name=om.upload_id
                )
                file_content = response.data  # Use .data instead of .read() for MinIO
                
                # extract the text and get the summary
                pdf_text = extract_text_from_pdf_stream(io.BytesIO(file_content))
                summary = generate_summary(
                    anthropic_client=anthropic,
                    pdf_text=pdf_text
                )

                # Update with success
                print("setting address to", summary['address'])
                om.address = summary['address']
                print("setting title to", summary['title'])
                om.title = summary['title']
                print("setting description to", summary['description'])
                om.description = summary['description']
                print("setting summary to", summary['summary'])
                om.summary = summary['summary']
                om.status = OmStatus.PROCESSED

            except Exception as e:
                logger.exception(f"failed to process om -- {om_id} | {e}")
                # if we're at max tries, mark as failed
                if job_try == max_tries:
                    om.status = OmStatus.FAILED
                raise
            finally:
                await session.commit()

    except Exception as e:
        logger.exception(f"failed to process om -- {om_id} | {e}")
        # retry with linear backoff
        raise Retry(defer=job_try * 5)
