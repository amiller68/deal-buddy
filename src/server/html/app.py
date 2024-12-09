from fastapi import APIRouter, Request, Depends, Path, HTTPException, Response, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette import status
import json

from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import OmStatus, User, Om
from src.state import AppState
from src.logger import RequestSpan
from ..deps import redis_client, require_logged_in_user, state, async_db, span, get_websocket_user, websocket_redis, websocket_db

router = APIRouter()
templates = Jinja2Templates(directory="templates/app")


@router.get("", response_class=HTMLResponse)  # Will match /app
def index(
    request: Request,
    user: User = Depends(require_logged_in_user),
    _state: AppState = Depends(state),
):
    # TODO: re-implement hot reloading
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user.dict(),
            "auth_logout_url": "/auth/logout",
            "initial_content": "content/dashboard.html",
        },
    )


@router.get("/om/{om_id}", response_class=HTMLResponse)  # Will match /app/om/{om_id}
async def om(
    request: Request,
    om_id: str = Path(...),
    poll: bool = False,
    user: User = Depends(require_logged_in_user),
    db: AsyncSession = Depends(async_db),
    span: RequestSpan = Depends(span),
):
    try:
        om = await Om.read(id=om_id, session=db, span=span)
        if not om:
            raise HTTPException(status_code=404, detail="OM not found")
        if om.user_id != user.id:
            raise HTTPException(
                status_code=403, detail="You are not authorized to access this OM"
            )

        # For HTMX polling requests
        if request.headers.get("HX-Request") and poll:
            if om.status != OmStatus.PROCESSED:
                return Response(status_code=204, headers={"HX-Trigger": "poll"})
            return templates.TemplateResponse(
                "content/om.html",
                {
                    "request": request,
                    "id": om.id,
                    "status": om.status,
                    "address": om.address,
                    "title": om.title,
                    "summary": om.summary,
                },
            )

        # For full page requests
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user": user.dict(),
                "auth_logout_url": "/auth/logout",
                "initial_content": "content/om.html",
                "id": om.id,
                "status": om.status,
                "address": om.address,
                "title": om.title,
                "summary": om.summary,
            },
        )
    except Exception as error:
        span.error(f"Error fetching OM: {str(error)}")
        raise HTTPException(status_code=404, detail="Not Found") from error


@router.get(
    "/content/{content}", response_class=HTMLResponse
)  # Will match /app/content/{content}
def content(
    request: Request,
    content: str = Path(...),
    user: User = Depends(require_logged_in_user),
    _db: AsyncSession = Depends(async_db),
    _span: RequestSpan = Depends(span),
):
    try:
        data = {"request": request}
        if content == "index":
            data["user"] = user.dict()
        # NOTE: we don't need to handle om-specific content here,
        #  but i feel like that logic should be encapsulated here / or this
        #  handler should follow whatever pattern is used there
        return templates.TemplateResponse(f"content/{content}.html", data)
    except Exception as error:
        raise HTTPException(status_code=404, detail="Not Found") from error


@router.get("/login", response_class=HTMLResponse)  # Will match /app/login
def login(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "auth_google_login_url": "/auth/google/login"},
    )


@router.websocket("/ws/om/{om_id}/progress")
async def om_progress_websocket(
    websocket: WebSocket,
    om_id: str,
    user: User = Depends(get_websocket_user),
    redis: Redis = Depends(websocket_redis),
    db: AsyncSession = Depends(websocket_db),
):
    """WebSocket endpoint for tracking OM processing progress"""
    await websocket.accept()
    
    try:
        # Validate OM ownership
        om = await Om.read(id=om_id, session=db)
        if not om or om.user_id != user.id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Subscribe to Redis channels
        pubsub = redis.pubsub()
        channels = [f"process_om_progress:{om_id}", f"process_om_status:{om_id}"]
        try:
            pubsub.subscribe(*channels)
        except redis.ConnectionError:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return
            
        try:
            # Listen for messages
            while True:
                message = pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        if "progress" in data:
                            progress = max(0, min(1, float(data["progress"])))
                            data["progress"] = round(progress * 100)
                        
                        await websocket.send_json(data)
                    except (json.JSONDecodeError, ValueError):
                        continue
                
                # Check if connection is still alive
                try:
                    await websocket.receive_text()
                except Exception:
                    break
                    
        finally:
            pubsub.unsubscribe(*channels)
            pubsub.close()
            
    except Exception as e:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
