from fastapi import APIRouter
from . import home, app

# Create main HTML router
router = APIRouter()

# Include sub-routers with prefixes
router.include_router(home.router, prefix="")  # Empty prefix for root routes
router.include_router(app.router, prefix="/app")  # /app prefix
