"""Validation and scoring helpers for flashcards."""

import re
from typing import List, Optional, Tuple

import numpy as np

from .constants import (
    BANNED_QUESTION_PATTERNS,
    MAX_ANSWER_WORDS,
    MAX_QUESTION_WORDS,
    MECHANISM_INDICATORS,
    META_REFERENCE_PATTERNS,
    VAGUE_ANSWER_PATTERNS,
)


def answer_echoes_question(question: str, answer: str) -> bool:
    """Check if answer is just restating the question without adding information."""
    q_lower = question.lower().strip()
    a_lower = answer.lower().strip()
    a_word_list = a_lower.split()
    for prefix in [
        "what is ",
        "what are ",
        "what was ",
        "what were ",
        "who is ",
        "who are ",
        "where is ",
        "where are ",
        "define ",
    ]:
        if q_lower.startswith(prefix):
            subject = q_lower[len(prefix) :].rstrip("?").strip()
            if a_lower == subject:
                return True
            if len(a_word_list) <= len(subject.split()) + 2:
                subject_words = set(subject.split())
                trivial = {"the", "a", "an", "is", "are"}
                extra = set(a_word_list) - subject_words - trivial
                if len(extra) == 0:
                    return True
            break
    return False


def normalize_text(text: str) -> str:
    """Normalize text for duplicate detection."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def contains_banned_phrase(text: str, patterns: List[str]) -> bool:
    """Check if text contains any banned phrase."""
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in patterns)


def validate_flashcard(question: str, answer: str) -> Tuple[bool, Optional[str]]:
    """Validate a single flashcard candidate."""
    q_text = (question or "").strip()
    a_text = (answer or "").strip()
    q_words = count_words(q_text)
    a_words = count_words(a_text)
    if q_words < 2 or a_words < 1:
        return False, "Question/answer too short"
    if not re.search(r"[a-zA-Z0-9]", q_text) or not re.search(r"[a-zA-Z0-9]", a_text):
        return False, "Question/answer missing content"
    q_clean = re.sub(r"[^a-z0-9_]+", "", q_text.lower())
    a_clean = re.sub(r"[^a-z0-9_]+", "", a_text.lower())
    banned_literals = {"question", "answer", "keypoint_index", "keypointindex"}
    if q_clean in banned_literals or a_clean in banned_literals:
        return False, "Question/answer contains placeholder key"

    if q_words > MAX_QUESTION_WORDS:
        return False, f"Question has {q_words} words (max {MAX_QUESTION_WORDS})"
    if a_words > MAX_ANSWER_WORDS:
        return False, f"Answer has {a_words} words (max {MAX_ANSWER_WORDS})"
    if a_words < 8:
        return False, "Answer too short (< 8 words); must be informative"
    if contains_banned_phrase(answer, META_REFERENCE_PATTERNS):
        return False, "Answer must not refer to 'review', 'the material', 'lecture', or 'as discussed'"

    has_mechanism = any(re.search(p, a_text.lower()) for p in MECHANISM_INDICATORS)
    has_number = bool(re.search(r"\d+", a_text))
    if not has_mechanism and not has_number:
        return False, "Answer must explain how/why or include concrete detail"
    if contains_banned_phrase(question, BANNED_QUESTION_PATTERNS):
        return False, "Question contains banned phrase (explain, describe, etc.)"
    if contains_banned_phrase(answer, VAGUE_ANSWER_PATTERNS):
        return False, "Answer is too vague"

    question_lower = q_text.lower().strip()
    if question_lower.startswith(("what do you think", "in your opinion")):
        return False, "Question is too generic/opinion-based"
    if question_lower.startswith(("{", "[")) or answer.lower().strip().startswith(("{", "[")):
        return False, "Question/answer appears to be JSON"
    if answer_echoes_question(question, answer):
        return False, "Answer must explain the concept, not just repeat the question"
    return True, None


def validate_flashcard_lenient(question: str, answer: str) -> bool:
    """Lenient validation for fallback when strict validation yields no cards."""
    q_text = (question or "").strip()
    a_text = (answer or "").strip()
    if count_words(q_text) < 2 or count_words(a_text) < 6:
        return False
    if not re.search(r"[a-zA-Z0-9]", q_text) or not re.search(r"[a-zA-Z0-9]", a_text):
        return False
    if contains_banned_phrase(answer, META_REFERENCE_PATTERNS):
        return False
    if answer_echoes_question(question, answer):
        return False
    if q_text.lower().startswith(("{", "[")) or a_text.lower().startswith(("{", "[")):
        return False
    q_clean = re.sub(r"[^a-z0-9_]+", "", q_text.lower())
    a_clean = re.sub(r"[^a-z0-9_]+", "", a_text.lower())
    banned = {"question", "answer", "keypoint_index", "keypointindex"}
    if q_clean in banned or a_clean in banned:
        return False
    return True


def compute_quality_score(question: str, answer: str, keypoint_text: Optional[str] = None) -> float:
    """Compute quality score for a flashcard candidate."""
    score = 0.0
    question_lower = question.lower().strip()
    good_starters = ["what", "which", "when", "where", "who", "how"]
    if any(question_lower.startswith(starter) for starter in good_starters):
        if not question_lower.startswith("how do you feel"):
            score += 1.0

    a_words = count_words(answer)
    if 20 <= a_words <= 45:
        score += 1.0
    elif 15 <= a_words < 20 or 45 < a_words <= 60:
        score += 0.5
    elif 10 <= a_words < 15:
        score += 0.25

    if any(re.search(p, answer.lower()) for p in MECHANISM_INDICATORS):
        score += 1.0

    if keypoint_text:
        keypoint_words = set(keypoint_text.lower().split())
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        if keypoint_words.intersection(question_words) or keypoint_words.intersection(answer_words):
            score += 1.0

    if "various" in answer.lower() or "several" in answer.lower() or "it depends" in answer.lower():
        score -= 2.0
    if any(x in answer.lower() for x in ("review", "material", "details")):
        score -= 2.0

    and_count = question.lower().count(" and ")
    comma_count = question.count(",")
    if and_count >= 2 and comma_count >= 1:
        score -= 1.0
    return score


def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    arr1 = np.array(vec1)
    arr2 = np.array(vec2)
    dot_product = np.dot(arr1, arr2)
    norm1 = np.linalg.norm(arr1)
    norm2 = np.linalg.norm(arr2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)
