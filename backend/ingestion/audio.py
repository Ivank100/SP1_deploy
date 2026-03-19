"""This file handles audio-specific ingestion work for lectures.
It covers transcription and turning spoken content into searchable text chunks."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Dict, List

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from ..core.config import OPENAI_API_KEY, OPENAI_BASE_URL, WHISPER_MODEL, WHISPER_USE_API


class TranscriptionError(RuntimeError):
    """Raised when Whisper transcription fails."""


def transcribe_audio(file_path: str) -> Dict[str, Any]:
    """
    Transcribe an audio file using local Whisper model (free) or OpenAI Whisper API.
    
    Tries local Whisper first (free), falls back to API if OPENAI_API_KEY is set.
    Returns the verbose JSON payload (includes segments with timestamps).
    """
    resolved_path = Path(file_path).expanduser().resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Audio file not found: {resolved_path}")

    # Use API directly if forced via env var
    if WHISPER_USE_API:
        if OPENAI_API_KEY:
            return _transcribe_with_api(resolved_path)
        raise TranscriptionError("WHISPER_USE_API is set but OPENAI_API_KEY is missing")

    # Try local Whisper first (free)
    if WHISPER_AVAILABLE:
        try:
            return _transcribe_with_local_whisper(resolved_path)
        except Exception as e:
            # If local fails and API key exists, fall back to API
            if OPENAI_API_KEY:
                return _transcribe_with_api(resolved_path)
            raise TranscriptionError(f"Local Whisper failed: {e}")

    # Fall back to API if local Whisper not available
    if OPENAI_API_KEY:
        return _transcribe_with_api(resolved_path)
    
    raise TranscriptionError(
        "Neither local Whisper nor OpenAI API is available. "
        "Install openai-whisper: pip install openai-whisper"
    )


def _transcribe_with_local_whisper(file_path: Path) -> Dict[str, Any]:
    """Transcribe using local Whisper model (free)."""
    # Load model (downloads on first use)
    model = whisper.load_model("base")  # Options: tiny, base, small, medium, large
    
    # Transcribe
    result = model.transcribe(
        str(file_path),
        verbose=False,
        word_timestamps=True
    )
    
    # Convert to API-compatible format
    segments = []
    for segment in result.get("segments", []):
        segments.append({
            "id": segment.get("id", 0),
            "seek": segment.get("seek", 0),
            "start": segment.get("start", 0.0),
            "end": segment.get("end", 0.0),
            "text": segment.get("text", "").strip(),
            "tokens": segment.get("tokens", []),
            "temperature": segment.get("temperature", 0.0),
            "avg_logprob": segment.get("avg_logprob", 0.0),
            "compression_ratio": segment.get("compression_ratio", 0.0),
            "no_speech_prob": segment.get("no_speech_prob", 0.0),
        })
    
    return {
        "text": result.get("text", ""),
        "language": result.get("language", "en"),
        "segments": segments,
    }


def _transcribe_with_api(file_path: Path) -> Dict[str, Any]:
    """Transcribe using OpenAI Whisper API (requires credits)."""
    import requests
    
    url = f"{OPENAI_BASE_URL.rstrip('/')}/audio/transcriptions"
    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    data = {
        "model": WHISPER_MODEL,
        "response_format": "verbose_json",
    }

    with file_path.open("rb") as audio_file:
        files = {"file": (file_path.name, audio_file, mime_type)}
        response = requests.post(url, headers=headers, data=data, files=files, timeout=600)

    if response.status_code != 200:
        raise TranscriptionError(
            f"Whisper API returned {response.status_code}: {response.text}"
        )

    payload = response.json()
    if "segments" not in payload:
        raise TranscriptionError("Transcription payload missing 'segments'")
    return payload


def chunk_transcript_segments(
    transcript: Dict[str, Any],
    max_chars: int = 800,
) -> List[Dict[str, Any]]:
    """
    Convert Whisper transcript segments into RAG chunks with timestamp metadata.

    Chunks preserve temporal ordering and merge adjacent segments until max_chars.
    """
    segments = transcript.get("segments") or []
    if not segments:
        raise TranscriptionError("Transcript does not contain any segments to chunk")

    chunks: List[Dict[str, Any]] = []
    buffer: List[str] = []
    chunk_start: float | None = None
    chunk_end: float | None = None

    def flush():
        nonlocal buffer, chunk_start, chunk_end
        if not buffer or chunk_start is None or chunk_end is None:
            return
        chunks.append(
            {
                "text": " ".join(buffer).strip(),
                "timestamp_start": float(chunk_start),
                "timestamp_end": float(chunk_end),
            }
        )
        buffer = []
        chunk_start = None
        chunk_end = None

    for segment in segments:
        seg_text = (segment.get("text") or "").strip()
        if not seg_text:
            continue
        seg_start = float(segment.get("start", 0.0))
        seg_end = float(segment.get("end", seg_start))

        if chunk_start is None:
            chunk_start = seg_start
        chunk_end = seg_end
        buffer.append(seg_text)

        if len(" ".join(buffer)) >= max_chars:
            flush()

    flush()
    return chunks

