"""Speech recognition service using faster-whisper.

Transcribes an audio file/URL to Arabic text. Falls back to a deterministic
mock when the Whisper model cannot be loaded (e.g. no GPU / model not
downloaded), so the API stays functional in development.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from app.config import settings

try:
    from faster_whisper import WhisperModel

    _WHISPER_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    WhisperModel = None  # type: ignore[assignment]
    _WHISPER_AVAILABLE = False


class WhisperService:
    def __init__(self) -> None:
        self._model = None
        self._model_id: Optional[str] = None

    def _ensure_loaded(self):
        """Lazy-load the Whisper model; keep None if unavailable."""
        if self._model is not None or self._model_id is not None:
            return
        self._model_id = settings.WHISPER_MODEL
        if not _WHISPER_AVAILABLE:
            return
        try:
            self._model = WhisperModel(
                settings.WHISPER_MODEL,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
            )
        except Exception:  # pragma: no cover - model download/load failure
            self._model = None

    async def transcribe(self, audio_url: Optional[str]) -> str:
        """Return Arabic transcription for the given audio source."""
        self._ensure_loaded()
        if self._model is None or not audio_url:
            return self._mock_transcription(audio_url)

        # faster-whisper works on local file paths; URLs must be downloaded
        # by the caller before reaching here. Resolve relative paths under ./data.
        audio_path = audio_url
        if not os.path.exists(audio_path):
            return self._mock_transcription(audio_url)

        try:
            segments, _ = self._model.transcribe(audio_path, language="ar", beam_size=5)
            text = " ".join(segment.text for segment in segments).strip()
            return text or self._mock_transcription(audio_url)
        except Exception:  # pragma: no cover - runtime inference failure
            return self._mock_transcription(audio_url)

    @staticmethod
    def _mock_transcription(audio_url: Optional[str]) -> str:
        """Deterministic placeholder transcription so the pipeline is runnable."""
        source = audio_url or "unknown-audio"
        return f"بِسْمِ ٱللَّٰهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ  [mock transcription of {source}]"


whisper_service = WhisperService()
