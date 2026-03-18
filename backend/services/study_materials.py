import json
import re
import random
from typing import List, Dict, Any, Tuple, Optional

from ..db.postgres import (
    get_lecture,
    get_chunks_for_lecture,
    save_lecture_summary,
    save_lecture_key_points,
    replace_flashcards,
    list_flashcards,
    get_lecture_study_materials,
)
from ..clients.openai import OpenAIClient

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


def _is_valid_keypoint(text: str) -> bool:
    """Filter out JSON/code artifacts and other junk from key points."""
    t = (text or "").strip()
    if not t or len(t) < 2:
        return False
    junk = {"[", "]", "{", "}", "```", "```json", "json"}
    if t in junk or t.rstrip(",") in junk:
        return False
    if t.startswith("```") or t.startswith("{"):
        return False
    if re.match(r"^[\s\[\]\{\}\"\'\,\.\:\;\!\?\-]+$", t):
        return False
    return True


def _fallback_keypoints_repair(context: str) -> List[str]:
    """
    When JSON parsing fails, use LLM repair prompt instead of random sentence truncation.
    Produces higher quality key points than the old fallback.
    """
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
            points = [str(p).strip() for p in parsed if _is_valid_keypoint(str(p).strip())]
            return points[:8] if points else []
    except json.JSONDecodeError:
        pass
    # Last resort: extract capitalized terms and frequent phrases (deterministic)
    words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", context)
    seen = set()
    result = []
    for w in words:
        w = w.strip()
        if len(w.split()) >= 2 and len(w.split()) <= 8 and w.lower() not in seen:
            seen.add(w.lower())
            result.append(w)
            if len(result) >= 6:
                break
    return result[:6]


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


def _stratified_sample_chunks(
    chunks: List[Tuple[str, Optional[int], Optional[float], Optional[float]]],
    limit: int,
) -> List[Tuple[str, Optional[int], Optional[float], Optional[float]]]:
    """
    Sample chunks evenly across the lecture (early, mid, late) to avoid bias toward first 40.
    """
    if len(chunks) <= limit or limit <= 1:
        return chunks[:limit] if limit else chunks
    n = len(chunks)
    indices = []
    for i in range(limit):
        pos = int((i / (limit - 1)) * (n - 1))
        indices.append(min(pos, n - 1))
    return [chunks[i] for i in sorted(set(indices))]


def _prepare_context(
    lecture_id: int,
) -> Tuple[str, List[Tuple[str, Optional[int], Optional[float], Optional[float]]]]:
    # Fetch more chunks, then stratify to cover early/mid/late lecture
    all_chunks = get_chunks_for_lecture(lecture_id, limit=80)
    if not all_chunks:
        raise ValueError("No chunks found for lecture")
    chunks = _stratified_sample_chunks(all_chunks, MAX_CONTEXT_CHUNKS)
    context_lines = [
        f"{_chunk_reference(page, ts_start, ts_end)} {text.strip()}"
        for text, page, ts_start, ts_end in chunks
    ]
    context = "\n\n".join(context_lines)
    return context, chunks


def get_materials(lecture_id: int) -> Dict[str, Any]:
    materials = get_lecture_study_materials(lecture_id) or {"summary": None, "key_points": []}
    def is_bad_flashcard(text: str) -> bool:
        trimmed = (text or "").strip()
        if not trimmed or not re.search(r"[a-zA-Z0-9]", trimmed):
            return True
        cleaned = re.sub(r'[^a-z0-9_]+', '', trimmed.lower())
        return cleaned in {"question", "answer", "keypoint_index", "keypointindex"}
    
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
                    question = row[1] if len(row) > 1 else ""
                    answer = row[2] if len(row) > 2 else ""
                    if is_bad_flashcard(question) or is_bad_flashcard(answer):
                        continue
                    flashcards.append({
                        "id": row[0],
                        "question": question,
                        "answer": answer,
                        "front": question,
                        "back": answer,
                        "source_keypoint_id": row[3] if len(row) > 3 else None,
                        "quality_score": row[4] if len(row) > 4 else None,
                        "page_number": None,
                    })
                else:
                    # Old schema: (id, front, back, page_number)
                    question = row[1] if len(row) > 1 else ""
                    answer = row[2] if len(row) > 2 else ""
                    if is_bad_flashcard(question) or is_bad_flashcard(answer):
                        continue
                    flashcards.append({
                        "id": row[0],
                        "front": question,
                        "back": answer,
                        "question": question,
                        "answer": answer,
                        "page_number": row[3] if len(row) > 3 else None,
                    })
    
    raw_points = materials.get("key_points") or []
    key_points = [p for p in raw_points if isinstance(p, str) and _is_valid_keypoint(p)]
    return {
        "summary": materials["summary"],
        "key_points": key_points,
        "flashcards": flashcards,
    }


def generate_summary(lecture_id: int) -> str:
    _ensure_ready_lecture(lecture_id)
    context, _ = _prepare_context(lecture_id)
    client = OpenAIClient()
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
    summary = client.chat(messages, max_tokens=303).strip()
    save_lecture_summary(lecture_id, summary)
    return summary


def generate_key_points(lecture_id: int) -> List[str]:
    _ensure_ready_lecture(lecture_id)
    context, _ = _prepare_context(lecture_id)
    client = OpenAIClient()
    messages = [
        {
            "role": "system",
            "content": "You extract concise noun-phrase key points from lecture content.",
        },
        {
            "role": "user",
            "content": (
                "Output ONLY a JSON array of strings.\n"
                "Return 5-8 key points.\n"
                "Each key point must be a noun phrase (no full sentences).\n"
                "Up to 10 words each; allow structured phrases like 'Safe state condition in Banker's algorithm'.\n"
                "No ending period. No verbs like includes / involves / manages.\n"
                "No punctuation except / and -.\n"
                "Use lecture terminology only. Preserve conceptual anchors (e.g. 'Deadlock necessary conditions', 'Reusable vs consumable resources').\n\n"
                f"Context:\n{context}\n\nJSON array:"
            ),
        },
    ]
    response = client.chat(messages, max_tokens=303, temperature=0.3).strip()
    # Strip markdown code fences (```json, ```) that some models add
    response = re.sub(r"^```(?:json)?\s*", "", response)
    response = re.sub(r"\s*```\s*$", "", response).strip()

    key_points: List[str]
    try:
        parsed = json.loads(response)
        if isinstance(parsed, list):
            key_points = [str(item).strip() for item in parsed if _is_valid_keypoint(str(item))]
            key_points = key_points[:8]
        else:
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        key_points = [
            line.strip("-• ").strip("[],")
            for line in response.splitlines()
            if line.strip() and _is_valid_keypoint(line.strip("-• "))
        ]
        key_points = key_points[:8]
    if key_points:
        cleaned_points = []
        for point in key_points:
            cleaned = re.sub(r"^\s*\d+\.\s*", "", point).strip()
            cleaned = re.sub(r"[.]$", "", cleaned)  # Only trailing period
            # Reject items that START with weak verbs (don't truncate - that destroys meaning)
            lower = cleaned.lower()
            if re.match(r"^\s*(includes|involves|manages|covers|describes)\b", lower):
                continue
            words = cleaned.split()
            if len(words) > 10:
                cleaned = " ".join(words[:10])  # Allow slightly longer
            if cleaned and _is_valid_keypoint(cleaned):
                cleaned_points.append(cleaned)
        key_points = cleaned_points[:8]
    if not key_points:
        # Better fallback: LLM repair prompt instead of random sentence truncation
        key_points = _fallback_keypoints_repair(context)
    if not key_points:
        raise ValueError("Could not extract key points from model response")
    save_lecture_key_points(lecture_id, key_points)
    return key_points


def generate_flashcards(lecture_id: int) -> List[Dict[str, Any]]:
    _ensure_ready_lecture(lecture_id)
    context, chunks = _prepare_context(lecture_id)
    client = OpenAIClient()
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
    response = client.chat(messages, max_tokens=303).strip()

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
