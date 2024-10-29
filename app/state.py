from fastapi import (
    FastAPI,
    Request,
)
from dataclasses import dataclass
from fastapi_sso.sso.google import GoogleSSO
import anthropic
from enum import Enum as PyEnum


from app.database import (
    AsyncDatabase,
)
from app.config import Config, Secrets
from app.logger import Logger
from app.storage import Storage

class AppStateExceptionType(PyEnum):
    startup_failed = "startup_failed" # raised when startup fails

class AppStateException(Exception):
    def __init__(self, type: AppStateExceptionType, message: str):
        self.message = message
        self.type = type

@dataclass
class AppState:
    config: Config
    google_sso: GoogleSSO
    anthropic_client: anthropic.Client
    storage: Storage
    database: AsyncDatabase
    logger: Logger
    secrets: Secrets

    @classmethod
    def from_config(cls, config: Config):
        return cls(
            config=config,
            google_sso=GoogleSSO(
                config.secrets.google_client_id,
                config.secrets.google_client_secret,
                redirect_uri=f"{config.host_name}/auth/google/callback",
                allow_insecure_http=True,
            ),
            anthropic_client=anthropic.Client(api_key=config.secrets.anthropic_api_key),
            storage=Storage(config),
            database=AsyncDatabase(config.database_path),
            logger=Logger(config.log_path, config.debug),
            secrets=config.secrets
        )
    
    async def startup(self):
        """run any startup logic here"""
        try:
            await self.database.initialize()
            await self.storage.initialize()
        except Exception as e:
            raise AppStateException(AppStateExceptionType.startup_failed, str(e)) from e

    async def shutdown(self):
        """run any shutdown logic here"""
        pass

    def set_on_request(self, request: Request):
        """set any request-specific state here"""
        request.state.app_state = self

    def get_on_request(self, request: Request):
        """get any request-specific state here"""
        return request.state.app_state

