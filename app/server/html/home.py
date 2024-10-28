from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory="templates/home")

@router.get("/", response_class=HTMLResponse)
def index(request: Request):
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