"""This file stores helper logic shared by the study-material generators.
It keeps repeated prompt, formatting, and citation behavior in one place."""


import json
import re
from typing import Any, Dict, List, Optional, Tuple

from ...clients.openai import OpenAIClient
from ...db.postgres import (
    get_chunks_for_lecture,
    get_latest_flashcard_set,
    get_lecture,
    get_lecture_study_materials,
    list_flashcards_by_set,
)

MAX_CONTEXT_CHUNKS = 40


class LectureNotFoundError(Exception):
    """Raised when the requested lecture does not exist."""


class LectureNotReadyError(Exception):
    """Raised when a lecture has not finished processing."""


def ensure_ready_lecture(lecture_id: int):
    lecture = get_lecture(lecture_id)
    if not lecture:
        raise LectureNotFoundError(f"Lecture {lecture_id} not found")
    if lecture[4] != "completed":
        raise LectureNotReadyError(f"Lecture status is {lecture[4]}")
    return lecture


def format_timecode(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def is_valid_keypoint(text: str) -> bool:
    candidate = (text or "").strip()
    if not candidate or len(candidate) < 2:
        return False
    junk = {"[", "]", "{", "}", "```", "```json", "json"}
    if candidate in junk or candidate.rstrip(",") in junk:
        return False
    if candidate.startswith("```") or candidate.startswith("{"):
        return False
    if re.match(r"^[\s\[\]\{\}\"\'\,\.\:\;\!\?\-]+$", candidate):
        return False
    return True


def fallback_keypoints_repair(context: str) -> List[str]:
    client = OpenAIClient()
    messages = [
        {"role": "system", "content": "You extract study-relevant key points from lecture text. Output ONLY a JSON array of strings. Each item: noun phrase or short concept (3-10 words). No full sentences."},
        {"role": "user", "content": (
            "Extract 5-8 key points from this lecture context. "
            "Return ONLY a JSON array of strings, e.g. [\"concept A\", \"concept B\"].\n\n"
            f"Context:\n{context[:8000]}\n\nJSON array:"
        )},
    ]
    response = client.chat(messages, max_tokens=303, temperature=0.2).strip()
    response = re.sub(r"^```(?:json)?\s*", "", response)
    response = re.sub(r"\s*```\s*$", "", response).strip()
    try:
        parsed = json.loads(response)
        if isinstance(parsed, list):
            points = [str(point).strip() for point in parsed if is_valid_keypoint(str(point).strip())]
            return points[:8] if points else []
    except json.JSONDecodeError:
        pass

    words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", context)
    seen = set()
    result = []
    for word in words:
        word = word.strip()
        if len(word.split()) >= 2 and len(word.split()) <= 8 and word.lower() not in seen:
            seen.add(word.lower())
            result.append(word)
            if len(result) >= 6:
                break
    return result[:6]


def chunk_reference(page: Optional[int], ts_start: Optional[float], ts_end: Optional[float]) -> str:
    if page is not None:
        return f"[Page {page}]"
    if ts_start is not None:
        start = format_timecode(ts_start)
        if ts_end is not None and ts_end > ts_start:
            end = format_timecode(ts_end)
            if end != start:
                return f"[Time {start}-{end}]"
        return f"[Time {start}]"
    return "[Chunk]"


def stratified_sample_chunks(
    chunks: List[Tuple[str, Optional[int], Optional[float], Optional[float]]],
    limit: int,
) -> List[Tuple[str, Optional[int], Optional[float], Optional[float]]]:
    if len(chunks) <= limit or limit <= 1:
        return chunks[:limit] if limit else chunks
    chunk_count = len(chunks)
    indices = []
    for idx in range(limit):
        position = int((idx / (limit - 1)) * (chunk_count - 1))
        indices.append(min(position, chunk_count - 1))
    return [chunks[idx] for idx in sorted(set(indices))]


def prepare_context(
    lecture_id: int,
) -> Tuple[str, List[Tuple[str, Optional[int], Optional[float], Optional[float]]]]:
    all_chunks = get_chunks_for_lecture(lecture_id, limit=80)
    if not all_chunks:
        raise ValueError("No chunks found for lecture")
    chunks = stratified_sample_chunks(all_chunks, MAX_CONTEXT_CHUNKS)
    context_lines = [
        f"{chunk_reference(page, ts_start, ts_end)} {text.strip()}"
        for text, page, ts_start, ts_end in chunks
    ]
    return "\n\n".join(context_lines), chunks


def get_materials(lecture_id: int) -> Dict[str, Any]:
    materials = get_lecture_study_materials(lecture_id) or {"summary": None, "key_points": []}
    latest_set = get_latest_flashcard_set(lecture_id)
    flashcards = []
    if latest_set:
        set_id, _strategy, _created_by = latest_set
        for row in list_flashcards_by_set(set_id):
            question = (row[1] or "").strip()
            answer = (row[2] or "").strip()
            if not question or not answer:
                continue
            flashcards.append(
                {
                    "id": row[0],
                    "question": question,
                    "answer": answer,
                    "front": question,
                    "back": answer,
                    "source_keypoint_id": row[3],
                    "quality_score": row[4],
                    "page_number": None,
                }
            )

    raw_points = materials.get("key_points") or []
    key_points = [point for point in raw_points if isinstance(point, str) and is_valid_keypoint(point)]
    return {
        "summary": materials["summary"],
        "key_points": key_points,
        "flashcards": flashcards,
    }
