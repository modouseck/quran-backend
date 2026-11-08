"""Routes package __init__: re-export routers for clean imports."""

from app.routes import auth, progress, recitation, users

__all__ = ["auth", "progress", "recitation", "users"]
