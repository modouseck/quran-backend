"""Tajweed error-correction engine.

Compares a transcribed recitation against the reference Quranic text for the
given surah/ayah, detects word-level errors (substitution / deletion /
insertion), classifies them by a coarse Tajweed rule, and returns the
corrected text plus a confidence score.

Reference texts are embedded for a starter set of surahs (Al-Fatiha,
Al-Ikhlas, Al-Falaq, An-Nas) with a clear extension point to load the full
Quran from a JSON data file.
"""

from __future__ import annotations

import difflib
import json
import os
import re
from dataclasses import dataclass
from typing import List, Optional

from app.config import settings


# Minimal reference Quran text (Uthmani script). Extend by adding surahs here
# or by pointing TAJWEED_REFERENCE_PATH at a JSON file {surah: {ayah: text}}.
_EMBEDDED_REFERENCES = {
    1: {  # Al-Fatiha
        1: "بِسْمِ ٱللَّٰهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
        2: "ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَالَمِينَ",
        3: "ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
        4: "مَالِكِ يَوْمِ ٱلدِّينِ",
        5: "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ",
        6: "ٱهْدِنَا ٱلصِّرَاطَ ٱلْمُسْتَقِيمَ",
        7: "صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ",
    },
    112: {  # Al-Ikhlas
        1: "قُلْ هُوَ ٱللَّٰهُ أَحَدٌ",
        2: "ٱللَّهُ الصَّمَدُ",
        3: "لَمْ يَلِدْ وَلَمْ يُولَدْ",
        4: "وَلَمْ يَكُن لَّهُۥ كُفُوًا أَحَدٌۢ",
    },
    113: {  # Al-Falaq
        1: "قُلْ أَعُوذُ بِرَبِّ ٱلْفَلَقِ",
        2: "مِن شَرِّ مَا خَلَقَ",
        3: "وَمِن شَرِّ غَاسِقٍ إِذَا وَقَبَ",
        4: "وَمِن شَرِّ ٱلنَّفَّاثَاتِ فِي ٱلْعُقَدِ",
        5: "وَمِن شَرِّ حَاسِدٍ إِذَا حَسَدَ",
    },
    114: {  # An-Nas
        1: "قُلْ أَعُوذُ بِرَبِّ ٱلنَّاسِ",
        2: "مَلِكِ ٱلنَّاسِ",
        3: "إِلَٰهِ ٱلنَّاسِ",
        4: "مِن شَرِّ ٱلْوَسْوَاسِ ٱلْخَنَّاسِ",
        5: "الَّذِي يُوَسْوِسُ فِي صُدُورِ ٱلنَّاسِ",
        6: "مِنَ ٱلْجِنَّةِ وَٱلنَّاسِ",
    },
}


@dataclass
class CorrectionResult:
    transcribed_text: str
    corrected_text: str
    tajweed_errors: List[dict]
    tajweed_errors_json: str  # JSON string for DB storage
    confidence_score: float


def _normalize(text: str) -> str:
    """Normalize Arabic for comparison: strip diacritics/tatweel, collapse whitespace."""
    if not text:
        return ""
    # Remove Arabic diacritics (harakat) and tatweel for robust matching
    text = re.sub(r"[\u0617-\u061A\u064B-\u0652\u0640]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _words(text: str) -> List[str]:
    return _normalize(text).split() if _normalize(text) else []


def _load_references() -> dict:
    """Load references from TAJWEED_REFERENCE_PATH if present, else embedded."""
    path = settings.TAJWEED_MODEL_PATH  # reused as a data directory hint
    ref_file = os.path.join(path, "references.json") if path else None
    if ref_file and os.path.exists(ref_file):
        try:
            with open(ref_file, "r", encoding="utf-8") as f:
                return {int(k): v for k, v in json.load(f).items()}
        except Exception:
            pass
    return _EMBEDDED_REFERENCES


class TajweedEngine:
    def __init__(self) -> None:
        self._references: Optional[dict] = None

    def _references_loaded(self) -> dict:
        if self._references is None:
            self._references = _load_references()
        return self._references

    def reference_text(self, surah_number: int, ayah_number: int) -> Optional[str]:
        surah = self._references_loaded().get(surah_number)
        if surah is None:
            return None
        return surah.get(ayah_number)

    @staticmethod
    def _classify_rule(expected_word: str, transcribed_word: str) -> str:
        """Coarse Tajweed rule classification from the expected word."""
        # Very light heuristic keyed on letters present in the expected word.
        if any(ch in expected_word for ch in "ءأؤإ"):
            return "Hamzah"
        if any(ch in expected_word for ch in "قط"):
            return "Qalqalah"
        if any(ch in expected_word for ch in "غخ"):
            return "Ghunnah/Nasal"
        if "ا" in expected_word and len(expected_word) > 3:
            return "Madd"
        return "Articulation"

    def correct(
        self,
        surah_number: int,
        ayah_number: int,
        transcribed_text: str,
    ) -> CorrectionResult:
        reference = self.reference_text(surah_number, ayah_number)
        if reference is None:
            # No reference available: treat transcription as-is, low confidence.
            return CorrectionResult(
                transcribed_text=transcribed_text,
                corrected_text=transcribed_text,
                tajweed_errors=[],
                tajweed_errors_json="[]",
                confidence_score=0.5,
            )

        ref_words = _words(reference)
        hyp_words = _words(transcribed_text)

        errors: List[dict] = []
        sm = difflib.SequenceMatcher(a=ref_words, b=hyp_words, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            if tag == "replace":
                for ref_w, hyp_w in zip(ref_words[i1:i2], hyp_words[j1:j2]):
                    errors.append(
                        {
                            "ayah": ayah_number,
                            "word": hyp_w,
                            "expected": ref_w,
                            "rule": self._classify_rule(ref_w, hyp_w),
                            "confidence": round(sm.ratio(), 2),
                        }
                    )
                # Handle length mismatch within replace block
                if len(ref_words[i1:i2]) != len(hyp_words[j1:j2]):
                    longer = ref_words[i1:i2] if len(ref_words[i1:i2]) > len(hyp_words[j1:j2]) else hyp_words[j1:j2]
                    shorter = hyp_words[j1:j2] if len(ref_words[i1:i2]) > len(hyp_words[j1:j2]) else ref_words[i1:i2]
                    for w in longer[len(shorter):]:
                        errors.append(
                            {
                                "ayah": ayah_number,
                                "word": w if w in hyp_words[j1:j2] else "",
                                "expected": w if w in ref_words[i1:i2] else "",
                                "rule": "Omission" if w in ref_words[i1:i2] else "Addition",
                                "confidence": round(sm.ratio(), 2),
                            }
                        )
            elif tag == "delete":
                for w in ref_words[i1:i2]:
                    errors.append(
                        {
                            "ayah": ayah_number,
                            "word": "",
                            "expected": w,
                            "rule": "Omission",
                            "confidence": round(sm.ratio(), 2),
                        }
                    )
            elif tag == "insert":
                for w in hyp_words[j1:j2]:
                    errors.append(
                        {
                            "ayah": ayah_number,
                            "word": w,
                            "expected": "",
                            "rule": "Addition",
                            "confidence": round(sm.ratio(), 2),
                        }
                    )

        # Confidence: proportion of reference words matched exactly.
        matched = sum(1 for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag == "equal" for _ in ref_words[i1:i2])
        total_ref = len(ref_words) or 1
        confidence = round(min(1.0, matched / total_ref + 0.1), 2)

        return CorrectionResult(
            transcribed_text=transcribed_text,
            corrected_text=reference,
            tajweed_errors=errors,
            tajweed_errors_json=json.dumps(errors, ensure_ascii=False),
            confidence_score=confidence,
        )


tajweed_engine = TajweedEngine()
