"""
sarvam_voice.py
===============
Sarvam AI Text-to-Speech (TTS) Integration Engine.
Uses Sarvam AI API (model: bulbul:v3) to generate ultra-realistic, natural
Kannada (kn-IN) and Indian English (en-IN) human voice audio.

Supported Speakers on bulbul:v3:
- kavya (Female - Natural Warm Kannada/English)
- priya (Female - Expressive Clear Tone)
- aditya (Male - Deep Resonant Voice)
- rahul (Male - Friendly Conversational Tone)
- roopa (Female - Gentle Tone)
- ratan (Male - Grounded Rustic Voice)
"""

from __future__ import annotations

import base64
import os
from typing import Any, Dict, List, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

# Default voice settings
DEFAULT_SPEAKER = "kavya"
DEFAULT_MODEL = "bulbul:v3"
DEFAULT_PACE = 1.0
DEFAULT_SAMPLE_RATE = 22050

SUPPORTED_SPEAKERS = {
    "kavya": {"id": "kavya", "name": "Kavya (Female - Natural)", "gender": "Female"},
    "priya": {"id": "priya", "name": "Priya (Female - Expressive)", "gender": "Female"},
    "aditya": {"id": "aditya", "name": "Aditya (Male - Resonant)", "gender": "Male"},
    "rahul": {"id": "rahul", "name": "Rahul (Male - Friendly)", "gender": "Male"},
    "roopa": {"id": "roopa", "name": "Roopa (Female - Gentle)", "gender": "Female"},
    "ratan": {"id": "ratan", "name": "Ratan (Male - Grounded)", "gender": "Male"},
}


def get_available_speakers() -> List[Dict[str, str]]:
    """Return available Sarvam AI speakers with metadata."""
    return list(SUPPORTED_SPEAKERS.values())


def synthesize_speech(
    text: str,
    target_language_code: str = "kn-IN",
    speaker: str = "kavya",
    pace: float = 1.0,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Synthesize text to speech using Sarvam AI TTS API (bulbul:v3).

    Args:
        text: Input text string to speak (Kannada or English).
        target_language_code: "kn-IN" (Kannada) or "en-IN" (Indian English).
        speaker: Speaker identifier (e.g. "kavya", "priya", "aditya", "rahul", "roopa", "ratan").
        pace: Speed of speech between 0.7 and 1.3 (default 1.0).
        api_key: Optional override for Sarvam API key.

    Returns:
        Base64-encoded audio WAV string if successful, or None if failed/unconfigured.
    """
    key = api_key or os.getenv("SARVAM_API_KEY", SARVAM_API_KEY)
    if not key:
        return None

    clean_text = text.strip()
    if not clean_text:
        return None

    # Limit text length per chunk for voice output
    if len(clean_text) > 450:
        clean_text = clean_text[:450] + "..."

    headers = {
        "api-subscription-key": key,
        "Content-Type": "application/json"
    }

    # Normalize language code
    if "kn" in target_language_code.lower():
        lang_code = "kn-IN"
    else:
        lang_code = "en-IN"

    chosen_speaker = speaker if speaker in SUPPORTED_SPEAKERS else DEFAULT_SPEAKER

    payload = {
        "inputs": [clean_text],
        "target_language_code": lang_code,
        "speaker": chosen_speaker,
        "pitch": 0,
        "pace": max(0.7, min(1.3, float(pace))),
        "loudness": 1.0,
        "speech_sample_rate": DEFAULT_SAMPLE_RATE,
        "enable_preprocessing": True,
        "model": DEFAULT_MODEL
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(SARVAM_TTS_URL, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                audios = data.get("audios", [])
                if audios and len(audios) > 0:
                    return audios[0]
            else:
                print(f"[Sarvam TTS Warning] Status {response.status_code}: {response.text}")
                return None
    except Exception as err:
        print(f"[Sarvam TTS Exception] {err}")
        return None
