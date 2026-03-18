"""Structured flashcard generation pipeline exports."""

from .constants import CANDIDATE_COUNT, FINAL_COUNT_DEFAULT, MAX_SIMILARITY_THRESHOLD
from .orchestration import generate_flashcards_v2
from .parsing import parse_flashcard_candidates
from .selection import deduplicate_candidates, select_final_flashcards
from .validation import (
    answer_echoes_question,
    compute_cosine_similarity,
    compute_quality_score,
    count_words,
    normalize_text,
    validate_flashcard,
    validate_flashcard_lenient,
)

__all__ = [
    "CANDIDATE_COUNT",
    "FINAL_COUNT_DEFAULT",
    "MAX_SIMILARITY_THRESHOLD",
    "answer_echoes_question",
    "compute_cosine_similarity",
    "compute_quality_score",
    "count_words",
    "deduplicate_candidates",
    "generate_flashcards_v2",
    "normalize_text",
    "parse_flashcard_candidates",
    "select_final_flashcards",
    "validate_flashcard",
    "validate_flashcard_lenient",
]
