from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.exceptions import HTTPException  # Use Starlette's HTTPException
from starlette import status
from contextlib import asynccontextmanager

from fastapi.staticfiles import StaticFiles
from app.state import AppState
from .html import router as html_router
from .auth import router as auth_router
from .api import router as api_router

def create_app(state: AppState) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await state.database.initialize()
        yield
        await state.shutdown()

    async def state_middleware(request: Request, call_next):
        request.state.app_state = state
        return await call_next(request)

    async def storage_middleware(request: Request, call_next):
        request.state.storage = state.storage
        return await call_next(request)

    async def anthropic_client_middleware(request: Request, call_next):
        request.state.anthropic_client = state.anthropic_client
        return await call_next(request)

    async def span_middleware(request: Request, call_next):
        request.state.span = state.logger.get_request_span(request)
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            request.state.span.error(str(e))
            raise

    async def db_middleware(request: Request, call_next):
        async with state.database.session() as session:
            request.state.db = session
            try:
                response = await call_next(request)
                return response
            except Exception as e:
                await session.rollback()
                raise
            finally:
                await session.close()

    app = FastAPI(lifespan=lifespan)

    # Exception handler using the correct decorator syntax
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        print(f"Exception handler called: {exc.status_code} - {request.url.path}")  # Debug
        if request.url.path.startswith("/app"):
            if exc.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]:
                return RedirectResponse(
                    url="/app/login",
                    status_code=status.HTTP_302_FOUND
                )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    
    # Add middleware
    app.middleware("http")(state_middleware)
    app.middleware("http")(storage_middleware)
    app.middleware("http")(anthropic_client_middleware)
    app.middleware("http")(span_middleware)
    app.middleware("http")(db_middleware)
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Include the HTML router
    app.include_router(html_router)
    app.include_router(auth_router, prefix="/auth")
    app.include_router(api_router, prefix="/api")

    return app

# This instance is used by uvicorn
app = None
