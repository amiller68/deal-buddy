from arq import create_pool
from arq.connections import RedisSettings
from enum import Enum
from typing import Any


class TaskPriority(Enum):
    LOW = 10
    MEDIUM = 5
    HIGH = 1


class TaskManager:
    def __init__(self, redis_url: str, app_state: Any):
        self.redis_settings = RedisSettings.from_dsn(redis_url)
        self.redis_pool = None

    async def initialize(self):
        """Initialize Redis pool for enqueueing jobs"""
        self.redis_pool = await create_pool(self.redis_settings)

    async def shutdown(self):
        """Cleanup Redis pool"""
        if self.redis_pool:
            await self.redis_pool.close()

    # TODO: some sort of priority queue?
    async def process_om(self, om_id: str):
        """Enqueue an OM processing job"""
        if not self.redis_pool:
            raise RuntimeError("TaskManager not initialized")

        return await self.redis_pool.enqueue_job(
            "process_om",  # Must match function name in worker
            om_id,
        )
