"""
API endpoints for Meta MCP
"""

from .admin import router as admin_router
from .proxy import router as proxy_router

__all__ = [
    "admin_router",
    "proxy_router"
]