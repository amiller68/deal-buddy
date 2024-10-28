from fastapi import Request, Depends, HTTPException, Security
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_sso.sso.base import OpenID
from jose import jwt
from anthropic import Anthropic

from app.database.models import User
from app.storage import Storage
from app.logger import RequestSpan

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

async def get_logged_in_user(
    cookie: str = Security(APIKeyCookie(name=SESION_COOKIE_NAME)),
    async_db: AsyncSession = Depends(async_db),
    span: RequestSpan = Depends(span),
    state = Depends(state),
) -> User:
    try:
        claims = jwt.decode(
            cookie, 
            key=state.secrets.service_secret, 
            algorithms=["HS256"]
        )
        openid = OpenID(**claims["pld"])

        user = await User.read_by_email(
            email=openid.email, 
            session=async_db, 
            span=span
        )
        if not user:
            span.info(f"Creating new user: {openid.email}")
            user = await User.create(
                email=openid.email, 
                session=async_db, 
                span=span
            )
            await async_db.commit()

        return user
    except Exception as error:
        raise HTTPException(status_code=401, detail="Unauthorized") from error

async def require_logged_in_user(
    user: User = Depends(get_logged_in_user)
) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user
