"""Deduplication and selection helpers for flashcards."""

from typing import Any, Callable, Dict, List

from .constants import FINAL_COUNT_DEFAULT, MAX_SIMILARITY_THRESHOLD
from .validation import compute_cosine_similarity, normalize_text


def deduplicate_candidates(
    candidates: List[Dict[str, Any]],
    existing_questions: List[str],
    embedding_func: Callable[[List[str]], List[List[float]]],
) -> List[Dict[str, Any]]:
    """Remove duplicates using both exact matching and semantic similarity."""
    if not candidates:
        return []

    existing_normalized = {normalize_text(q): q for q in existing_questions}
    candidate_questions = [candidate.get("question", "") for candidate in candidates]
    candidate_embeddings = embedding_func(candidate_questions)

    existing_embeddings = None
    if existing_questions:
        existing_embeddings = embedding_func(existing_questions)

    filtered = []
    seen_normalized = set()
    seen_embeddings = []

    for index, candidate in enumerate(candidates):
        question = candidate.get("question", "")
        if not question:
            continue

        normalized = normalize_text(question)
        if normalized in existing_normalized or normalized in seen_normalized:
            continue

        candidate_embedding = candidate_embeddings[index]
        is_duplicate = False
        if existing_embeddings:
            for existing_embedding in existing_embeddings:
                if compute_cosine_similarity(candidate_embedding, existing_embedding) > MAX_SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break

        if not is_duplicate:
            for seen_embedding in seen_embeddings:
                if compute_cosine_similarity(candidate_embedding, seen_embedding) > MAX_SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break

        if not is_duplicate:
            filtered.append(candidate)
            seen_normalized.add(normalized)
            seen_embeddings.append(candidate_embedding)

    return filtered


def select_final_flashcards(
    candidates: List[Dict[str, Any]],
    target_count: int = FINAL_COUNT_DEFAULT,
    max_per_keypoint: int = 2,
) -> List[Dict[str, Any]]:
    """Select final flashcards while spreading coverage across key points."""
    if len(candidates) <= target_count:
        return candidates

    by_keypoint: Dict[int, List[Dict[str, Any]]] = {}
    no_keypoint = []
    for candidate in candidates:
        keypoint_index = candidate.get("keypoint_index")
        if keypoint_index is not None:
            by_keypoint.setdefault(keypoint_index, []).append(candidate)
        else:
            no_keypoint.append(candidate)

    for keypoint_index in by_keypoint:
        by_keypoint[keypoint_index].sort(
            key=lambda candidate: candidate.get("quality_score", 0.0),
            reverse=True,
        )

    selected = []
    keypoint_indices = list(by_keypoint.keys())
    keypoint_positions = {keypoint_index: 0 for keypoint_index in keypoint_indices}

    while len(selected) < target_count and (by_keypoint or no_keypoint):
        for keypoint_index in keypoint_indices:
            if len(selected) >= target_count:
                break
            if keypoint_index not in by_keypoint:
                continue

            current_count = sum(
                1 for selected_candidate in selected if selected_candidate.get("keypoint_index") == keypoint_index
            )
            if current_count >= max_per_keypoint:
                continue

            position = keypoint_positions[keypoint_index]
            if position < len(by_keypoint[keypoint_index]):
                selected.append(by_keypoint[keypoint_index][position])
                keypoint_positions[keypoint_index] += 1

        if len(selected) < target_count:
            if max_per_keypoint >= 2:
                max_per_keypoint += 1
                continue
            if no_keypoint:
                selected.append(no_keypoint.pop(0))
            else:
                break

    selected.sort(key=lambda candidate: candidate.get("quality_score", 0.0), reverse=True)
    return selected[:target_count]
