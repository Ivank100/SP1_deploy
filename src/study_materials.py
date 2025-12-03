import json
from typing import List, Dict, Any, Tuple, Optional

from .db import (
    get_lecture,
    get_chunks_for_lecture,
    save_lecture_summary,
    save_lecture_key_points,
    replace_flashcards,
    list_flashcards,
    get_lecture_study_materials,
)
from .deepseek_client import DeepSeekClient

MAX_CONTEXT_CHUNKS = 40


class LectureNotFoundError(Exception):
    """Raised when the requested lecture does not exist."""


class LectureNotReadyError(Exception):
    """Raised when a lecture has not finished processing."""


def _ensure_ready_lecture(lecture_id: int):
    lecture = get_lecture(lecture_id)
    if not lecture:
        raise LectureNotFoundError(f"Lecture {lecture_id} not found")
    if lecture[4] != "completed":
        raise LectureNotReadyError(f"Lecture status is {lecture[4]}")
    return lecture


def _format_timecode(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _chunk_reference(page: Optional[int], ts_start: Optional[float], ts_end: Optional[float]) -> str:
    if page is not None:
        return f"[Page {page}]"
    if ts_start is not None:
        start = _format_timecode(ts_start)
        if ts_end is not None and ts_end > ts_start:
            end = _format_timecode(ts_end)
            if end != start:
                return f"[Time {start}-{end}]"
        return f"[Time {start}]"
    return "[Chunk]"


def _prepare_context(
    lecture_id: int,
) -> Tuple[str, List[Tuple[str, Optional[int], Optional[float], Optional[float]]]]:
    chunks = get_chunks_for_lecture(lecture_id, limit=MAX_CONTEXT_CHUNKS)
    if not chunks:
        raise ValueError("No chunks found for lecture")
    context_lines = [
        f"{_chunk_reference(page, ts_start, ts_end)} {text.strip()}"
        for text, page, ts_start, ts_end in chunks
    ]
    context = "\n\n".join(context_lines)
    return context, chunks


def get_materials(lecture_id: int) -> Dict[str, Any]:
    materials = get_lecture_study_materials(lecture_id) or {"summary": None, "key_points": []}
    flashcards = [
        {"id": row[0], "front": row[1], "back": row[2], "page_number": row[3]}
        for row in list_flashcards(lecture_id)
    ]
    return {
        "summary": materials["summary"],
        "key_points": materials["key_points"],
        "flashcards": flashcards,
    }


def generate_summary(lecture_id: int) -> str:
    _ensure_ready_lecture(lecture_id)
    context, _ = _prepare_context(lecture_id)
    client = DeepSeekClient()
    messages = [
        {
            "role": "system",
            "content": "You create concise study summaries from lecture excerpts.",
        },
        {
            "role": "user",
            "content": (
                "Create a clear summary (3-5 short paragraphs) of the following lecture context. "
                "Do not introduce information that is not in the text.\n\n"
                f"Context:\n{context}\n\nSummary:"
            ),
        },
    ]
    summary = client.chat(messages).strip()
    save_lecture_summary(lecture_id, summary)
    return summary


def generate_key_points(lecture_id: int) -> List[str]:
    _ensure_ready_lecture(lecture_id)
    context, _ = _prepare_context(lecture_id)
    client = DeepSeekClient()
    messages = [
        {
            "role": "system",
            "content": "You extract key bullet points from lecture content.",
        },
        {
            "role": "user",
            "content": (
                "Read the context and return 5-8 essential key points as a JSON array of strings. "
                "Each key point should be concise (max 25 words) and reflect the lecture content only.\n\n"
                f"Context:\n{context}\n\nJSON array:"
            ),
        },
    ]
    response = client.chat(messages).strip()
    key_points: List[str]
    try:
        parsed = json.loads(response)
        if isinstance(parsed, list):
            key_points = [str(item).strip() for item in parsed][:8]
        else:
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        key_points = [line.strip("-• ") for line in response.splitlines() if line.strip()]
        key_points = key_points[:8]
    if not key_points:
        raise ValueError("Could not extract key points from model response")
    save_lecture_key_points(lecture_id, key_points)
    return key_points


def generate_flashcards(lecture_id: int) -> List[Dict[str, Any]]:
    _ensure_ready_lecture(lecture_id)
    context, chunks = _prepare_context(lecture_id)
    client = DeepSeekClient()
    messages = [
        {
            "role": "system",
            "content": "You create study flashcards from lecture content.",
        },
        {
            "role": "user",
            "content": (
                "Using the context, create 5 high-quality flashcards that help students study. "
                "Return a JSON array where each item has fields "
                '`"front"` (question), `"back"` (answer), and `"page_number"` (page reference if possible). '
                "Reference only the provided content.\n\n"
                f"Context:\n{context}\n\nJSON array:"
            ),
        },
    ]
    response = client.chat(messages).strip()
    try:
        parsed = json.loads(response)
        if not isinstance(parsed, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        raise ValueError("Failed to parse flashcards response as JSON")

    flashcards: List[Tuple[str, str, Any]] = []
    for item in parsed[:5]:
        if not isinstance(item, dict):
            continue
        front = item.get("front") or item.get("question")
        back = item.get("back") or item.get("answer")
        page = item.get("page_number") or item.get("page")
        if not front or not back:
            continue
        flashcards.append((str(front).strip(), str(back).strip(), int(page) if page else None))

    if not flashcards:
        raise ValueError("No valid flashcards returned by model")

    replace_flashcards(lecture_id, flashcards)
    stored = [
        {"id": row[0], "front": row[1], "back": row[2], "page_number": row[3]}
        for row in list_flashcards(lecture_id)
    ]
    return stored

