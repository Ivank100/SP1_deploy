"""This file handles retrieving relevant lecture chunks for a question.
It is the search step that finds the best source material before answer generation."""


from collections import defaultdict
import re
from typing import Any, Dict, List, Optional, Tuple

from ...db.postgres import search_similar
from ..embeddings import embed_texts
from .constants import (
    DEFAULT_CITATION_MAX_DISTANCE,
    DEFAULT_CITATION_TOP_K,
    KEYPOINT_QUESTION_PATTERNS,
    PAGE_CONTENT_HINT_PATTERNS,
    PAGE_LOOKUP_PATTERNS,
    REFERENCE_PATTERNS,
    STOP_WORDS,
    matches_any_pattern,
)


def extract_keywords(question: str, limit: int = 6) -> List[str]:
    tokens = [t.lower() for t in question.replace("?", " ").replace(".", " ").split()]
    keywords = [t for t in tokens if t not in STOP_WORDS and len(t) > 3]
    deduped = []
    for token in keywords:
        if token not in deduped:
            deduped.append(token)
    return deduped[:limit]


def _normalize_result(result: Tuple[Any, ...]) -> Dict[str, Any]:
    text, page_number, lect_id, lect_name, file_type, ts_start, ts_end, *rest = result
    distance = rest[0] if rest else None
    return {
        "text": text,
        "lecture_id": lect_id,
        "lecture_name": lect_name,
        "file_type": file_type,
        "page_number": page_number,
        "timestamp_start": ts_start,
        "timestamp_end": ts_end,
        "distance": distance,
    }


def _build_sources(
    results: List[Dict[str, Any]]
) -> List[Dict[str, Optional[int] | str | Optional[float]]]:
    return [
        {
            "lecture_id": result["lecture_id"],
            "lecture_name": result["lecture_name"],
            "file_type": result["file_type"],
            "page_number": result["page_number"],
            "timestamp_start": result["timestamp_start"],
            "timestamp_end": result["timestamp_end"],
        }
        for result in results
    ]


def select_citation_sources(
    results: List[Tuple[Any, ...]],
    limit: int = DEFAULT_CITATION_TOP_K,
) -> List[Dict[str, Optional[int] | str | Optional[float]]]:
    normalized_results = [_normalize_result(result) for result in results]
    if not normalized_results:
        return []

    best_distance = min(
        result["distance"] for result in normalized_results if result["distance"] is not None
    ) if any(result["distance"] is not None for result in normalized_results) else None

    page_scores: Dict[Tuple[Any, ...], float] = defaultdict(float)
    best_result_by_ref: Dict[Tuple[Any, ...], Dict[str, Any]] = {}

    for result in normalized_results:
        if not result["text"].strip():
            continue
        ref_key = (
            result["lecture_id"],
            result["page_number"],
            result["timestamp_start"],
            result["timestamp_end"],
        )
        distance = result["distance"]
        if distance is not None and best_distance is not None:
            if distance > max(DEFAULT_CITATION_MAX_DISTANCE, best_distance + 0.12):
                continue
            score = 1.0 / max(distance + 1e-6, 1e-6)
        else:
            score = 1.0

        page_scores[ref_key] += score
        current_best = best_result_by_ref.get(ref_key)
        if current_best is None or (
            distance is not None and (
                current_best["distance"] is None or distance < current_best["distance"]
            )
        ):
            best_result_by_ref[ref_key] = result

    ranked_refs = sorted(page_scores.items(), key=lambda item: item[1], reverse=True)

    selected_results = []
    for ref_key, _score in ranked_refs:
        result = best_result_by_ref[ref_key]
        if result in selected_results:
            continue
        selected_results.append(result)
        if len(selected_results) >= limit:
            break

    return _build_sources(selected_results)


def extract_reference_patterns(question: str) -> List[str]:
    patterns: List[str] = []
    lowered = question.lower()

    for raw_pattern in REFERENCE_PATTERNS:
        for match in re.finditer(raw_pattern, lowered):
            ref_num = match.group(1)
            prefix = lowered[match.start():match.end()].split()[0]
            if prefix.startswith("q"):
                patterns.extend(
                    [
                        rf"\bquestion\s*[:.#-]?\s*{ref_num}\b",
                        rf"\bq\s*[:.#-]?\s*{ref_num}\b",
                        rf"\b{ref_num}\s*[\).:-]",
                    ]
                )
            elif prefix == "page":
                patterns.append(rf"\bpage\s*[:.#-]?\s*{ref_num}\b")
            elif prefix == "slide":
                patterns.append(rf"\bslide\s*[:.#-]?\s*{ref_num}\b")

    deduped: List[str] = []
    for pattern in patterns:
        if pattern not in deduped:
            deduped.append(pattern)
    return deduped


def extract_explicit_page_reference(question: str) -> Optional[int]:
    lowered = question.lower()
    matches: List[int] = []
    for pattern in PAGE_LOOKUP_PATTERNS:
        matches.extend(int(match.group(1)) for match in re.finditer(pattern, lowered))

    unique_matches = sorted(set(matches))
    if len(unique_matches) == 1:
        return unique_matches[0]
    return None


def is_page_content_request(question: str) -> bool:
    lowered = question.lower()
    has_page_ref = extract_explicit_page_reference(question) is not None
    if not has_page_ref:
        return False
    return matches_any_pattern(lowered, PAGE_CONTENT_HINT_PATTERNS)


def build_page_content_answer(
    page_number: int,
    results: List[Tuple[Any, ...]],
) -> str:
    parts: List[str] = []
    for result in results:
        text = str(result[0]).strip()
        if text:
            parts.append(text)

    body = "\n\n".join(parts).strip()
    if not body:
        return f"I found page {page_number}, but it does not contain extracted text."
    return f"Here is the extracted content from page {page_number}:\n\n{body}"


def is_key_points_question(question: str) -> bool:
    return matches_any_pattern(question.lower(), KEYPOINT_QUESTION_PATTERNS)


def extract_requested_keypoint_numbers(question: str, total_keypoints: int) -> List[int]:
    if total_keypoints <= 0:
        return []

    matches: List[int] = []
    for match in re.finditer(r"\b(?:key\s*point|point|concept)\s*(\d{1,2})\b", question.lower()):
        value = int(match.group(1))
        if 1 <= value <= total_keypoints:
            matches.append(value)

    deduped: List[int] = []
    for value in matches:
        if value not in deduped:
            deduped.append(value)
    return deduped


def build_keypoint_answer_prompt(
    question: str,
    lecture_id: int,
    course_id: Optional[int],
    key_points: List[str],
) -> tuple[str, List[Tuple[Any, ...]]]:
    requested_numbers = extract_requested_keypoint_numbers(question, len(key_points))
    if requested_numbers:
        selected = [(index, key_points[index - 1]) for index in requested_numbers]
    else:
        selected = list(enumerate(key_points, start=1))

    retrieval_results: List[Tuple[Any, ...]] = []
    selected_with_results: List[Tuple[int, str, List[Tuple[Any, ...]]]] = []
    for keypoint_index, key_point in selected:
        [keypoint_embedding] = embed_texts([key_point])
        keypoint_results = search_similar(
            keypoint_embedding,
            top_k=2,
            lecture_id=lecture_id,
            course_id=course_id,
        )
        selected_with_results.append((keypoint_index, key_point, keypoint_results))
        for result in keypoint_results:
            if result not in retrieval_results:
                retrieval_results.append(result)

    keypoint_lines = [f"{index}. {text}" for index, text in selected]
    context_sections: List[str] = []
    for index, key_point, related_chunks in selected_with_results:
        excerpt_lines = [f"- {str(chunk[0]).strip()}" for chunk in related_chunks if str(chunk[0]).strip()]
        section = [f"Key point {index}: {key_point}"]
        if excerpt_lines:
            section.append("Related lecture excerpts:")
            section.extend(excerpt_lines)
        context_sections.append("\n".join(section))

    prompt = (
        "These key points were previously generated for this lecture.\n\n"
        f"Stored key points:\n" + "\n".join(keypoint_lines) + "\n\n"
        "Use the lecture excerpts to elaborate on the relevant key points.\n"
        "Keep the explanation grounded in the provided excerpts, organize it clearly, and make it useful for studying.\n"
        "If the user asks about specific numbered key points, focus on those.\n\n"
        f"Question: {question}\n\n"
        f"Lecture support:\n{'\n\n'.join(context_sections)}"
    )
    return prompt, retrieval_results
