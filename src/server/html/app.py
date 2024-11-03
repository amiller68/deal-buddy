from fastapi import APIRouter, Request, Depends, Path, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from src.database.models import User
from src.state import AppState
from ..deps import require_logged_in_user, state

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
            "initial_content": "dashboard.html",
        },
    )

@router.get("/content/{content}", response_class=HTMLResponse)  # Will match /app/content/{content}
def content(request: Request, content: str = Path(...), user: User = Depends(require_logged_in_user)):
    try:
        data = {"request": request}
        if content == "index":
            data["user"] = user.dict()
        return templates.TemplateResponse(f"content/{content}.html", data)
    except Exception as error:
        raise HTTPException(status_code=404, detail="Not Found") from error

@router.get("/login", response_class=HTMLResponse)  # Will match /app/login
def login(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "auth_google_login_url": "/auth/google/login"},
    )