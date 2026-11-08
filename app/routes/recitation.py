"""Recitation routes: submit audio, get analysis (ASR + tajweed correction), history."""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import get_current_active_user
from app.database import get_session
from app.models import Progress, Recitation, User
from app.schemas import (
    RecitationAnalysisResult,
    RecitationAnalyze,
    RecitationCreate,
    RecitationOut,
    RecitationUpdate,
    TajweedError,
)
from app.services.tajweed_engine import tajweed_engine
from app.services.whisper_service import whisper_service

router = APIRouter(prefix="/recitations", tags=["recitations"])

UPLOAD_DIR = "data/uploads"


@router.post("/analyze", response_model=RecitationAnalysisResult, status_code=status.HTTP_201_CREATED)
async def analyze_recitation(
    recitation_in: RecitationAnalyze,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    # 1. Speech-to-text via Whisper (mocked fallback if model unavailable)
    transcription = await whisper_service.transcribe(recitation_in.audio_url)

    # 2. Quran-aware error correction via tajweed engine
    correction = tajweed_engine.correct(
        surah_number=recitation_in.surah_number,
        ayah_number=recitation_in.ayah_number,
        transcribed_text=transcription,
    )

    recitation = Recitation(
        user_id=current_user.id,
        surah_number=recitation_in.surah_number,
        ayah_number=recitation_in.ayah_number,
        audio_url=recitation_in.audio_url,
        transcribed_text=correction.transcribed_text,
        corrected_text=correction.corrected_text,
        tajweed_errors=correction.tajweed_errors,
        confidence_score=correction.confidence_score,
    )
    session.add(recitation)
    await session.commit()
    await session.refresh(recitation)

    # Update / upsert progress
    result = await session.execute(
        select(Progress).where(
            Progress.user_id == current_user.id,
            Progress.surah_number == recitation_in.surah_number,
            Progress.ayah_number == recitation_in.ayah_number,
        )
    )
    progress = result.scalar_one_or_none()
    error_count = len(correction.tajweed_errors)
    if progress is None:
        progress = Progress(
            user_id=current_user.id,
            surah_number=recitation_in.surah_number,
            ayah_number=recitation_in.ayah_number,
            recitation_count=1,
            tajweed_error_count=error_count,
        )
        session.add(progress)
    else:
        progress.recitation_count += 1
        progress.tajweed_error_count += error_count
        progress.last_recited_at = recitation.created_at
    session.add(progress)
    await session.commit()

    return RecitationAnalysisResult(
        surah_number=recitation_in.surah_number,
        ayah_number=recitation_in.ayah_number,
        transcribed_text=correction.transcribed_text,
        corrected_text=correction.corrected_text,
        tajweed_errors=correction.tajweed_errors,
        confidence_score=correction.confidence_score,
    )


@router.post("/analyze/voice", response_model=RecitationAnalysisResult, status_code=status.HTTP_201_CREATED)
async def analyze_voice(
    surah_number: int = Form(..., ge=1, le=114),
    ayah_number: int = Form(..., ge=1),
    audio: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    # 1. Save uploaded audio to disk
    import os
    import shutil

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(
        UPLOAD_DIR, f"{current_user.id}_{surah_number}_{ayah_number}_{audio.filename}"
    )
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    # 2. Speech-to-text via Whisper
    transcription = await whisper_service.transcribe(file_path)

    # 3. Quran-aware error correction via tajweed engine
    correction = tajweed_engine.correct(
        surah_number=surah_number,
        ayah_number=ayah_number,
        transcribed_text=transcription,
    )

    recitation = Recitation(
        user_id=current_user.id,
        surah_number=surah_number,
        ayah_number=ayah_number,
        audio_url=file_path,
        transcribed_text=correction.transcribed_text,
        corrected_text=correction.corrected_text,
        tajweed_errors=correction.tajweed_errors,
        confidence_score=correction.confidence_score,
    )
    session.add(recitation)
    await session.commit()
    await session.refresh(recitation)

    # Update / upsert progress
    result = await session.execute(
        select(Progress).where(
            Progress.user_id == current_user.id,
            Progress.surah_number == surah_number,
            Progress.ayah_number == ayah_number,
        )
    )
    progress = result.scalar_one_or_none()
    error_count = len(correction.tajweed_errors)
    if progress is None:
        progress = Progress(
            user_id=current_user.id,
            surah_number=surah_number,
            ayah_number=ayah_number,
            recitation_count=1,
            tajweed_error_count=error_count,
        )
        session.add(progress)
    else:
        progress.recitation_count += 1
        progress.tajweed_error_count += error_count
        progress.last_recited_at = recitation.created_at
    session.add(progress)
    await session.commit()

    return RecitationAnalysisResult(
        surah_number=surah_number,
        ayah_number=ayah_number,
        transcribed_text=correction.transcribed_text,
        corrected_text=correction.corrected_text,
        tajweed_errors=correction.tajweed_errors,
        confidence_score=correction.confidence_score,
    )


@router.get("/", response_model=List[RecitationOut])
async def list_recitations(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
    surah_number: Optional[int] = None,
    ayah_number: Optional[int] = None,
):
    stmt = select(Recitation).where(Recitation.user_id == current_user.id).order_by(Recitation.created_at.desc())
    if surah_number is not None:
        stmt = stmt.where(Recitation.surah_number == surah_number)
    if ayah_number is not None:
        stmt = stmt.where(Recitation.ayah_number == ayah_number)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{recitation_id}", response_model=RecitationOut)
async def get_recitation(
    recitation_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(Recitation).where(Recitation.id == recitation_id, Recitation.user_id == current_user.id)
    )
    recitation = result.scalar_one_or_none()
    if recitation is None:
        raise HTTPException(status_code=404, detail="Recitation not found")
    return recitation


@router.put("/{recitation_id}", response_model=RecitationOut)
async def update_recitation(
    recitation_id: int,
    recitation_in: RecitationUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(Recitation).where(Recitation.id == recitation_id, Recitation.user_id == current_user.id)
    )
    recitation = result.scalar_one_or_none()
    if recitation is None:
        raise HTTPException(status_code=404, detail="Recitation not found")

    for field, value in recitation_in.model_dump(exclude_unset=True).items():
        setattr(recitation, field, value)

    session.add(recitation)
    await session.commit()
    await session.refresh(recitation)
    return recitation
