import json
import re
import random
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
    
    # Get flashcards - handle both old and new schema
    flashcard_rows = list_flashcards(lecture_id)
    flashcards = []
    for row in flashcard_rows:
        if len(row) >= 4:
            # Check if it's new schema (question/answer) or old (front/back)
            if hasattr(row, '__iter__') and len(row) > 3:
                # New schema: (id, question, answer, source_keypoint_id, quality_score)
                if len(row) >= 3 and row[1] and not hasattr(row[1], '__len__') or isinstance(row[1], str):
                    # Likely new schema
                    flashcards.append({
                        "id": row[0],
                        "question": row[1] if len(row) > 1 else "",
                        "answer": row[2] if len(row) > 2 else "",
                        "front": row[1] if len(row) > 1 else "",
                        "back": row[2] if len(row) > 2 else "",
                        "source_keypoint_id": row[3] if len(row) > 3 else None,
                        "quality_score": row[4] if len(row) > 4 else None,
                        "page_number": None,
                    })
                else:
                    # Old schema: (id, front, back, page_number)
                    flashcards.append({
                        "id": row[0],
                        "front": row[1] if len(row) > 1 else "",
                        "back": row[2] if len(row) > 2 else "",
                        "question": row[1] if len(row) > 1 else "",
                        "answer": row[2] if len(row) > 2 else "",
                        "page_number": row[3] if len(row) > 3 else None,
                    })
    
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
    summary = client.chat(messages, max_tokens=1200).strip()
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
            "Read the context and return a NEW set of 3-5 essential key points as a JSON array of strings. "
            "Avoid repeating the exact same sentences; vary wording when possible. "
                "Each key point should be concise (max 25 words) and reflect the lecture content only.\n\n"
                f"Context:\n{context}\n\nJSON array:"
            ),
        },
    ]
    response = client.chat(messages, max_tokens=800, temperature=0.6).strip()
    key_points: List[str]
    try:
        parsed = json.loads(response)
        if isinstance(parsed, list):
            key_points = [str(item).strip() for item in parsed][:5]
        else:
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        key_points = [line.strip("-• ") for line in response.splitlines() if line.strip()]
        key_points = key_points[:5]
    if key_points:
        key_points = [re.sub(r"^\s*\d+\.\s*", "", point).strip() for point in key_points]
        key_points = [point for point in key_points if point]
        key_points = key_points[:5]
    if not key_points:
        # Fallback: derive concise points from context when model response is unusable
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", context.strip()) if s.strip()]
        random.shuffle(sentences)
        fallback_points = []
        for sentence in sentences:
            cleaned = re.sub(r"\s+", " ", sentence).strip()
            if not cleaned:
                continue
            words = cleaned.split()
            if len(words) > 25:
                cleaned = " ".join(words[:25]) + "..."
            fallback_points.append(cleaned)
            if len(fallback_points) >= 5:
                break
        key_points = fallback_points[:5]
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
    response = client.chat(messages, max_tokens=1200).strip()

    def _normalize_flashcard(text: str) -> Tuple[str, str]:
        cleaned = re.sub(r"^\s*\d+\.\s*", "", text).strip()
        for splitter in [":", " - ", " — "]:
            if splitter in cleaned:
                left, right = cleaned.split(splitter, 1)
                left = left.strip()
                right = right.strip()
                if left and right:
                    return left, right
        return "", ""

    parsed: Any = None
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        parsed = None

    flashcards: List[Tuple[str, str, Any]] = []
    if isinstance(parsed, list):
        for item in parsed[:5]:
            if isinstance(item, dict):
                front = item.get("front") or item.get("question")
                back = item.get("back") or item.get("answer")
                page = item.get("page_number") or item.get("page")
                if front and back:
                    flashcards.append((str(front).strip(), str(back).strip(), int(page) if page else None))
            elif isinstance(item, str):
                front, back = _normalize_flashcard(item)
                if front and back:
                    flashcards.append((front, back, None))
    else:
        for line in response.splitlines():
            if not line.strip():
                continue
            front, back = _normalize_flashcard(line)
            if front and back:
                flashcards.append((front, back, None))

    if not flashcards:
        raise ValueError("No valid flashcards returned by model")

    replace_flashcards(lecture_id, flashcards)
    stored = [
        {"id": row[0], "front": row[1], "back": row[2], "page_number": row[3]}
        for row in list_flashcards(lecture_id)
    ]
    return stored

