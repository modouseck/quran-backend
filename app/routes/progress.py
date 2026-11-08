"""Progress routes: per-user recitation progress per ayah."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import get_current_active_user
from app.database import get_session
from app.models import Progress
from app.schemas import ProgressOut

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/", response_model=List[ProgressOut])
async def list_progress(
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_active_user),
    surah_number: Optional[int] = None,
):
    stmt = select(Progress).where(Progress.user_id == current_user.id).order_by(Progress.updated_at.desc())
    if surah_number is not None:
        stmt = stmt.where(Progress.surah_number == surah_number)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{surah_number}/{ayah_number}", response_model=ProgressOut)
async def get_progress(
    surah_number: int,
    ayah_number: int,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_active_user),
):
    result = await session.execute(
        select(Progress).where(
            Progress.user_id == current_user.id,
            Progress.surah_number == surah_number,
            Progress.ayah_number == ayah_number,
        )
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        raise HTTPException(status_code=404, detail="Progress not found")
    return progress
