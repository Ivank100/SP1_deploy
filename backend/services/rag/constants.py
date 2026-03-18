import re

SYSTEM_PROMPT = """You are a helpful assistant for students studying lecture material.
You are given context extracted from lecture slides or PDFs. Use this context as your primary source.
If the answer is not covered in the context, answer using your general knowledge — do not refuse or say you don't know.
Do not include page numbers or source references in your answer — citations are handled separately.

IMPORTANT: Start your response with exactly one of these two tags (then a newline), before writing anything else:
[FROM_SLIDES] — if your answer is based on the provided lecture context
[GENERAL] — if your answer is based on your general knowledge because the context did not cover the question"""

STOP_WORDS = {
    "the", "a", "an", "is", "are", "to", "of", "in", "on", "for", "and", "or", "with",
    "what", "why", "how", "when", "where", "who", "which", "can", "could", "should", "would",
}

DEFAULT_CONTEXT_TOP_K = 10
DEFAULT_CITATION_TOP_K = 3
DEFAULT_CITATION_MAX_DISTANCE = 0.35

REFERENCE_PATTERNS = (
    r"\bquestion\s*(\d{1,3})\b",
    r"\bq(?:uestion)?\s*#?\s*(\d{1,3})\b",
    r"\bpage\s*(\d{1,4})\b",
    r"\bslide\s*(\d{1,4})\b",
)

PAGE_LOOKUP_PATTERNS = (
    r"\bpage\s*(\d{1,4})\b",
    r"\bslide\s*(\d{1,4})\b",
)

PAGE_CONTENT_HINT_PATTERNS = (
    r"\bcontent(?:s)?\b",
    r"\btext\b",
    r"\bwhat(?:'s|\s+is)?\s+on\b",
    r"\bwhat\s+does\b",
    r"\bsay\b",
    r"\bshow\b",
    r"\bgive\b",
    r"\bdisplay\b",
    r"\bextract\b",
    r"\bread\b",
    r"\bfull\b",
)

KEYPOINT_QUESTION_PATTERNS = (
    r"\bkey\s*points?\b",
    r"\bmain\s*points?\b",
    r"\bimportant\s*points?\b",
    r"\bkey\s*concepts?\b",
    r"\bmain\s*concepts?\b",
)


def strip_source_tag(answer: str) -> tuple[str, bool]:
    used_slides = True
    if answer.startswith("[FROM_SLIDES]"):
        answer = answer[len("[FROM_SLIDES]"):].lstrip("\n")
    elif answer.startswith("[GENERAL]"):
        answer = answer[len("[GENERAL]"):].lstrip("\n")
        used_slides = False
    return answer, used_slides


def matches_any_pattern(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)
