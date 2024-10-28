from fastapi import APIRouter
from . import oms

# Create main HTML router
router = APIRouter()

# Include sub-routers with prefixes
router.include_router(oms.router, prefix="/oms")
