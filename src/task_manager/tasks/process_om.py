import io

# used by dependency
import json
from arq import Retry
from dataclasses import asdict

from src.database.models import Om, OmStatus
from src.database.models.om_table import OmTable
from src.storage import StorageBucket
from src.llm.engines.om.engine import OmEngine, ProgressEvent


async def process_om(ctx, om_id: str, max_tries: int = 5):
    """Process an OM document"""
    storage = ctx["storage"]
    anthropic = ctx["anthropic"]
    redis = ctx["redis"]
    database = ctx["database"]
    job_try = ctx["job_try"]
    logger = ctx["logger"].get_worker_logger(name="process_om", attempt=job_try)

    async def progress_callback(event: ProgressEvent):
        """Publish progress events to Redis"""
        try:
            await redis.publish(
                "process_om_progress",
                json.dumps({
                    "om_id": om_id,
                    **asdict(event)
                })
            )
        except Exception as e:
            logger.exception(f"Failed to publish progress event: {e}")

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
                    "process_om_status",
                    json.dumps({"om_id": om_id, "status": OmStatus.PROCESSING}),
                )
            except Exception as e:
                logger.exception(
                    f"failed to publish status update for om -- {om_id} | {e}"
                )
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
                    bucket=StorageBucket.oms, object_name=om.storage_object_id
                )
                file_content = response.data  # Use .data instead of .read() for MinIO

                # extract the text and get the summary
                engine = OmEngine(
                    anthropic_client=anthropic,
                    progress_callback=progress_callback
                )
                context = await engine.process_pdf(io.BytesIO(file_content))

                # Update with success
                om.address = context.address
                om.title = context.title
                om.description = context.description
                om.summary = context.running_summary
                om.square_feet = context.square_feet
                om.total_units = context.total_units
                om.property_type = context.property_type
                om.status = OmStatus.PROCESSED

                # create tables
                await OmTable.create_many(
                    om_id=om.id,
                    tables=context.tables,
                    session=session,
                    storage=storage,
                )

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
