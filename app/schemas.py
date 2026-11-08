"""Pydantic schemas for request / response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=6, max_length=128)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, min_length=3, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=200)
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Recitation ----------
class TajweedError(BaseModel):
    ayah: int
    word: str
    expected: str
    rule: Optional[str] = None
    confidence: float


class RecitationCreate(BaseModel):
    surah_number: int = Field(ge=1, le=114)
    ayah_number: int = Field(ge=1)
    audio_url: Optional[str] = None


class RecitationUpdate(BaseModel):
    transcribed_text: Optional[str] = None
    corrected_text: Optional[str] = None
    tajweed_errors: Optional[List[TajweedError]] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class RecitationOut(BaseModel):
    id: int
    user_id: int
    surah_number: int
    ayah_number: int
    audio_url: Optional[str] = None
    transcribed_text: Optional[str] = None
    corrected_text: Optional[str] = None
    tajweed_errors: Optional[List[TajweedError]] = None
    confidence_score: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecitationAnalyze(BaseModel):
    surah_number: int = Field(ge=1, le=114)
    ayah_number: int = Field(ge=1)
    audio_url: Optional[str] = None


class RecitationAnalysisResult(BaseModel):
    surah_number: int
    ayah_number: int
    transcribed_text: str
    corrected_text: str
    tajweed_errors: List[TajweedError]
    confidence_score: float


# ---------- Progress ----------
class ProgressOut(BaseModel):
    user_id: int
    surah_number: int
    ayah_number: int
    last_recited_at: Optional[datetime] = None
    recitation_count: int
    tajweed_error_count: int
    updated_at: datetime

    model_config = {"from_attributes": True}
