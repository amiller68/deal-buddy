from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.state import AppState
from ..deps import state

router = APIRouter()
templates = Jinja2Templates(directory="templates/home")

@router.get("/", response_class=HTMLResponse)
def index(request: Request, _state: AppState = Depends(state)):
    # NOTE: special carve out for serving index content back to the app
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("index_content.html", {"request": request})
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("todo_content.html", {"request": request})
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "initial_content": "todo_content.html"}
    )

@router.get("/blog", response_class=HTMLResponse)
def blog(request: Request):
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("todo_content.html", {"request": request})
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "initial_content": "todo_content.html"}
    )