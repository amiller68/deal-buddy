from fastapi import Request, Depends, HTTPException, Security, WebSocket, WebSocketException, status
from fastapi.security import APIKeyCookie
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_sso.sso.base import OpenID
from jose import jwt
from anthropic import Anthropic

from src.database.models import User
from src.storage import Storage
from src.logger import RequestSpan
from src.task_manager import TaskManager

SESION_COOKIE_NAME = "session"


def async_db(request: Request) -> AsyncSession:
    return request.state.db


def span(request: Request) -> RequestSpan:
    return request.state.span


def state(request: Request):
    return request.state.app_state


def storage(request: Request) -> Storage:
    return request.state.storage


def anthropic_client(request: Request) -> Anthropic:
    return request.state.anthropic_client


def task_manager(request: Request) -> TaskManager:
    return request.state.task_manager

def redis_client(request: Request) -> Redis:
    return request.state.redis_client


async def get_logged_in_user(
    cookie: str = Security(APIKeyCookie(name=SESION_COOKIE_NAME)),
    async_db: AsyncSession = Depends(async_db),
    span: RequestSpan = Depends(span),
    state=Depends(state),
) -> User:
    try:
        claims = jwt.decode(
            cookie, key=state.secrets.service_secret, algorithms=["HS256"]
        )
        openid = OpenID(**claims["pld"])

        if not openid.email:
            raise ValueError("Email is required")

        user = await User.read_by_email(email=openid.email, session=async_db, span=span)
        if not user:
            span.info(f"Creating new user: {openid.email}")
            user = await User.create(email=openid.email, session=async_db, span=span)
            await async_db.commit()

        return user
    except Exception as error:
        raise HTTPException(status_code=401, detail="Unauthorized") from error


async def require_logged_in_user(user: User = Depends(get_logged_in_user)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def websocket_db(websocket: WebSocket) -> AsyncSession:
    return websocket.state.db

def websocket_span(websocket: WebSocket) -> RequestSpan:
    return websocket.state.span

def websocket_state(websocket: WebSocket):
    return websocket.state.app_state

def websocket_storage(websocket: WebSocket) -> Storage:
    return websocket.state.storage

def websocket_redis(websocket: WebSocket) -> Redis:
    return websocket.state.redis_client

async def get_websocket_user(
    websocket: WebSocket,
    db: AsyncSession = Depends(websocket_db),
    span: RequestSpan = Depends(websocket_span),
    state=Depends(websocket_state),
) -> User:
    """Similar to get_logged_in_user but for WebSocket connections"""
    try:
        # Get cookie directly from WebSocket headers
        cookies = dict(cookie.split("=", 1) for cookie in 
                      websocket.headers.get("cookie", "").split("; ") if cookie)
        cookie_value = cookies.get(SESION_COOKIE_NAME)
        
        if not cookie_value:
            raise ValueError("No session cookie found")

        claims = jwt.decode(
            cookie_value, key=state.secrets.service_secret, algorithms=["HS256"]
        )
        openid = OpenID(**claims["pld"])

        if not openid.email:
            raise ValueError("Email is required")

        user = await User.read_by_email(email=openid.email, session=db, span=span)
        if not user:
            raise ValueError("User not found")

        return user
    except Exception as error:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION) from error

async def require_websocket_user(
    websocket: WebSocket,
    user: User = Depends(get_websocket_user)
) -> User:
    """Dependency to ensure WebSocket user is authenticated"""
    if not user:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return user
