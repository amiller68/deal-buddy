from fastapi import APIRouter, Request, Depends, Path, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, Om
from src.state import AppState
from src.logger import RequestSpan
from ..deps import require_logged_in_user, state, async_db, span

router = APIRouter()
templates = Jinja2Templates(directory="templates/app")

@router.get("", response_class=HTMLResponse)  # Will match /app
def index(request: Request, user: User = Depends(require_logged_in_user), _state: AppState = Depends(state)):
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
async def om(request: Request, om_id: str = Path(...), user: User = Depends(require_logged_in_user), db: AsyncSession = Depends(async_db), span: RequestSpan = Depends(span)):
    try:
        print(f"om_id: {om_id}")
        om = await Om.read(id=om_id, session=db, span=span)
        print(f"om: {om}")
        if om.user_id != user.id:
            raise HTTPException(status_code=403, detail="You are not authorized to access this OM")
        # return templates.TemplateResponse("content/om.html", {"request": request, "status": om.status, "title": om.title, "description": om.description, "summary": om.summary})
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user": user.dict(),
                "initial_content": "content/om.html",
                "id": om.id,
                "status": om.status,
                "title": om.title,
                "description": om.description,
                "summary": om.summary,
            },
        )
    except Exception as error:
        raise HTTPException(status_code=404, detail="Not Found") from error

@router.get("/content/{content}", response_class=HTMLResponse)  # Will match /app/content/{content}
def content(request: Request, content: str = Path(...), user: User = Depends(require_logged_in_user), db: AsyncSession = Depends(async_db), span: RequestSpan = Depends(span)):
    try:
        data = {"request": request}
        if content == "index":
            data["user"] = user.dict()
        if content == "om":
            om = Om.read(id=request.query_params.get("id"), session=db, span=span)
            if om.user_id != user.id:
                raise HTTPException(status_code=403, detail="You are not authorized to access this OM")
            data["status"] = om.status
            data["title"] = om.title
            data["description"] = om.description
            data["summary"] = om.summary
        return templates.TemplateResponse(f"content/{content}.html", data)
    except Exception as error:
        raise HTTPException(status_code=404, detail="Not Found") from error

@router.get("/login", response_class=HTMLResponse)  # Will match /app/login
def login(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "auth_google_login_url": "/auth/google/login"},
    )