"""FastAPI application wiring: routers, middleware, startup/shutdown."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routes import auth, progress, recitation, users

app = FastAPI(
    title="Quran Recitation Backend",
    description="Backend with speech recognition and Tajweed error correction for Quran recitation.",
    version="0.1.0",
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(recitation.router)
app.include_router(progress.router)


@app.on_event("startup")
async def on_startup():
    """Create tables on startup (dev convenience; use Alembic migrations in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/", tags=["health"])
async def health():
    return {"status": "ok", "service": "quran-backend"}
