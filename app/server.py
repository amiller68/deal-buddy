from fastapi import Depends, FastAPI, Request, Response, Security, Path, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi_sso.sso.google import GoogleSSO
from fastapi.security import APIKeyCookie
from fastapi_sso.sso.base import OpenID
from starlette import status
from starlette.exceptions import HTTPException
from fastapi.exception_handlers import http_exception_handler
import datetime
import io
import anthropic
import PyPDF2

from database.models import Om, OmStatus
from database.database import AsyncSession
from storage import Storage, StorageBucket

def extract_text_from_pdf_stream(pdf_stream):
    reader = PyPDF2.PdfReader(pdf_stream)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text


from anthropic import Anthropic
from jose import jwt

import sys

sys.path.append("./database")
sys.path.append(".")

from database.database import (
    AsyncDatabase,
    DatabaseException,
    DatabaseExceptionType as db_e_type,
)
from database.models import (
    User
)
from config import Config
from logger import Logger, RequestSpan
from storage import Storage, StorageBucket, StorageException

# Constants

SESION_COOKIE_NAME = "session"


# App State

try:
    CONFIG = Config()
    print("DATABASE_PATH: ", CONFIG.database_path)
    print("MINIO_ENDPOINT: ", CONFIG.minio_endpoint)
    print("LOG_PATH: ", CONFIG.log_path)
    print("HOST_NAME: ", CONFIG.host_name)
    print("LISTEN_ADDRESS: ", CONFIG.listen_address)
    print("LISTEN_PORT: ", CONFIG.listen_port)
    print("MINIO_ENDPOINT: ", CONFIG.minio_endpoint)

    ANTHROPIC_CLIENT = anthropic.Client(api_key=CONFIG.secrets.anthropic_api_key)
    STORAGE = Storage(CONFIG)
    DATABASE = AsyncDatabase(CONFIG.database_path)
    LOGGER = Logger(CONFIG.log_path, CONFIG.debug)
    APP = FastAPI()
except Exception as e:
    print("Error setting up APP: ", e)
    exit(1)


# Exceptions


@APP.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == status.HTTP_403_FORBIDDEN and request.scope[
        "path"
    ].startswith("/app"):
        return RedirectResponse(url="/app/login")
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED and request.scope[
        "path"
    ].startswith("/app"):
        return RedirectResponse(url="/app/login")
    # Instead of calling itself, return a JSON response
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Middleware


@APP.middleware("http")
async def async_db_middleware(request: Request, call_next):
    try:
        async with DATABASE.AsyncSession() as session:
            request.state.db = session
            response = await call_next(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
    finally:
        await request.state.db.close()
    return response


@APP.middleware("http")
async def span_middleware(request: Request, call_next):
    response = Response("Internal server error", status_code=500)
    try:
        request.state.span = LOGGER.get_request_span(request)
        response = await call_next(request)
    finally:
        pass
    return response


# Dependencies


def google_sso():
    return GoogleSSO(
        CONFIG.secrets.google_client_id,
        CONFIG.secrets.google_client_secret,
        redirect_uri=f"{CONFIG.host_name}/auth/google/callback",
        # TODO: fix this by adding dev mode
        allow_insecure_http=True,
    )

def async_db(request: Request):
    return request.state.db


def span(request: Request):
    return request.state.span

async def get_logged_in_user(
    cookie: str = Security(APIKeyCookie(name=SESION_COOKIE_NAME)),
    async_db: AsyncSession = Depends(async_db),
    span: RequestSpan = Depends(span)
) -> User:
    try:
        claims = jwt.decode(
            cookie, key=CONFIG.secrets.service_secret, algorithms=["HS256"]
        )
        openid = OpenID(**claims["pld"])

         # Check if user exists in database
        user = await User.read_by_email(email=openid.email, session=async_db, span=span)
        if not user:
            span.info(f"server::get_logged_in_user::creating new user:  {openid.email}")
            # User doesn't exist, create a new one
            user = await User.create(email=openid.email, session=async_db, span=span)
            await async_db.commit()
        
        return user
    except Exception as error:
        raise HTTPException(status_code=401, detail="Unauthorized") from error

async def require_logged_in_user(user: User = Depends(get_logged_in_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

# Auth Routes

## Catch All


@APP.get("/auth/logout")
async def auth_logout():
    response = RedirectResponse(url="/app/login")
    response.delete_cookie(SESION_COOKIE_NAME)
    return response


## Google Auth


@APP.get("/auth/google/callback")
async def auth_google_callback(request: Request, google_sso=Depends(google_sso)):
    openid = await google_sso.verify_and_process(request)
    if not openid:
        raise HTTPException(status_code=401, detail="Unauthorized")
    expiration = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(
        days=1
    )
    token = jwt.encode(
        {"pld": openid.dict(), "exp": expiration, "sub": openid.id},
        key=CONFIG.secrets.service_secret,
        algorithm="HS256",
    )
    response = RedirectResponse(url="/app")
    response.set_cookie(
        key=SESION_COOKIE_NAME, value=token, expires=expiration
    )  # This cookie will make sure /protected knows the user
    return response


@APP.get("/auth/google/login")
async def auth_google_login(google_sso=Depends(google_sso)):
    return await google_sso.get_login_redirect()


# HTML ROUTES

## APP ROUTES

app_templates = Jinja2Templates(directory="templates/app")

### APP PAGES

@APP.get("/app", response_class=HTMLResponse)
def app_index(request: Request, user: User = Depends(get_logged_in_user)):
    user_info = user.dict()
    return app_templates.TemplateResponse(
        "index.html",
        {
            "request": request, 
            "user": user_info, 
            "auth_logout_url": "/auth/logout",
            "initial_content": "dashboard.html"  # Add this line
        },
    )

@APP.get("/app/settings", response_class=HTMLResponse)
def app_index(request: Request, user: User = Depends(get_logged_in_user)):
    return app_templates.TemplateResponse(
        "settings.html",
        {"request": request, "auth_logout_url": "/auth/logout"},
    )

### APP Content

@APP.get("/app/content/{content}", response_class=HTMLResponse)
def app_content(request: Request, content: str = Path(...), user: User = Depends(get_logged_in_user)):
    try:
        # NOTE: this seems kinda janky, but generally i expect content / components
        #  to be filled in with server rendered data, so I suppose I'll do so here.
        #   I should find a batter way to do this at the very least
        data = { "request": request }
        if content == "index":
            print(user.dict())
            data["user"] = user.dict()
        return app_templates.TemplateResponse(
            f"content/{content}.html",
            data
        )
    except Exception as error:
        print(error)
        raise HTTPException(status_code=404, detail="Not Found") from error

### APP Components
    
### APP LOGIN


@APP.get("/app/login", response_class=HTMLResponse)
def app_login(request: Request):
    return app_templates.TemplateResponse(
        "login.html",
        {"request": request, "auth_google_login_url": "/auth/google/login"},
    )


## HOME PAGE ROUTES

home_templates = Jinja2Templates(directory="templates/home")


### Index Page


@APP.get("/", response_class=HTMLResponse)
def home_index(request: Request):
    # Check if htmx request
    if request.headers.get("HX-Request"):
        return home_templates.TemplateResponse(
            "index_content.html", {"request": request}
        )
    return home_templates.TemplateResponse("index.html", {"request": request})

## Header Menu

### About Page


@APP.get("/about", response_class=HTMLResponse)
def home_about(request: Request):
    # Check if htmx request
    if request.headers.get("HX-Request"):
        return home_templates.TemplateResponse(
            # TODO: make this the actual about page
            "todo_content.html", {"request": request}
        )
    return home_templates.TemplateResponse("index.html", {
        "request": request,
        "initial_content": "todo_content.html"
    })

### Blog Page


@APP.get("/blog", response_class=HTMLResponse)
def home_blog(request: Request):
    # Check if htmx request
    if request.headers.get("HX-Request"):
        return home_templates.TemplateResponse(
            # TODO: make this the actual blog page
            "todo_content.html", {"request": request}
        )
    return home_templates.TemplateResponse("index.html", {
        "request": request,
        "initial_content": "todo_content.html"
    })


# Static Files

APP.mount("/static", StaticFiles(directory="static"), name="static")

# API Routes

API_VERSION = "v0"
API_PATH = f"api/{API_VERSION}"

### Om

@APP.post("/api/v0/om")
async def api_om(
    file: UploadFile = File(...),
    user: User = Depends(require_logged_in_user),
    span: RequestSpan = Depends(span),
    db: AsyncSession = Depends(async_db)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        # Read the file content
        content = await file.read()
        file_size = len(content)

        # Upload to MinIO
        upload_id = STORAGE.put_object(
            stream=io.BytesIO(content),
            stream_len=file_size,
            bucket=StorageBucket.oms
        )

        # Extract text from PDF
        pdf_text = extract_text_from_pdf_stream(io.BytesIO(content))

        user_id = user.id
        print(f"user_id: {user_id}")
        # Create Om record in database
        om = await Om.create(
            user_id=user.id,
            upload_id=upload_id,
            session=db,
            span=span
        )
        await db.commit()

        # TODO: Process the PDF text (e.g., send to AI for analysis)

        return {"message": "Om uploaded successfully", "om_id": om.id}

    except StorageException as e:
        span.error(f"Storage error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")
    except Exception as e:
        span.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@APP.get("/api/v0/oms")
async def api_get_oms(
    user: User = Depends(require_logged_in_user),
    span: RequestSpan = Depends(span),
    db: AsyncSession = Depends(async_db)
):
    try:
        oms = await Om.read_by_user_id(user_id=user.id, session=db, span=span)
        return [om.dict() for om in oms]
    except Exception as e:
        span.error(f"Error fetching OMs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch OMs")

# Run

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(APP, host=CONFIG.listen_address, port=CONFIG.listen_port,  proxy_headers=True)
