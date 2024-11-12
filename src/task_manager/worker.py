from arq.connections import RedisSettings
from src.logger import Logger
from src.task_manager.tasks.process_om import process_om
from src.config import Config
from src.database import AsyncDatabase
from src.storage import Storage
from anthropic import Anthropic

async def startup(ctx):
    """Initialize worker context"""
    config = Config()
    ctx['database'] = AsyncDatabase(config.database_path)
    ctx['storage'] = Storage(config)
    ctx['anthropic'] = Anthropic(api_key=config.secrets.anthropic_api_key)
    ctx['logger'] = Logger(config.log_path, config.debug, worker=True)
    await ctx['database'].initialize()
    await ctx['storage'].initialize()

async def shutdown(ctx):
    """Cleanup worker context"""
    pass

class WorkerSettings:
    """ARQ Worker Settings"""
    functions = [process_om]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn('redis://localhost:6379')
    
    # Worker configuration
    max_jobs = 10
    job_timeout = 300
    keep_result = 3600
    job_retry = True
    max_tries = 3
    health_check_interval = 30
    health_check_key = 'arq:health-check'
