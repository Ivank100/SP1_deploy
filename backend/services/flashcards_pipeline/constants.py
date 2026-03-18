"""Constants for flashcard generation."""

from ...core.config import FLASHCARD_COUNT_MAX

MAX_QUESTION_WORDS = 25
MAX_ANSWER_WORDS = 80
CANDIDATE_COUNT = 24
FINAL_COUNT_DEFAULT = FLASHCARD_COUNT_MAX
MAX_SIMILARITY_THRESHOLD = 0.90

BANNED_QUESTION_PATTERNS = [
    r"\bexplain\s+(?:in\s+)?detail\b",
    r"\bdescribe\s+(?:fully|in\s+detail)\b",
    r"\bdiscuss\b",
    r"\belaborate\b",
    r"\bhow would you\b",
    r"\bwhat do you think\b",
    r"\bin your opinion\b",
    r"\bhow do you feel\b",
    r"\bwrite about\b",
]

VAGUE_ANSWER_PATTERNS = [
    r"\bvarious\b",
    r"\bseveral\b",
    r"\bit depends\b",
]

META_REFERENCE_PATTERNS = [
    r"\breview\b",
    r"\bsee\s+(?:the\s+)?lecture\b",
    r"\bthe\s+material\b",
    r"\bas\s+discussed\b",
    r"\brefer\s+to\s+(?:the\s+)?(?:lecture|material)\b",
]

MECHANISM_INDICATORS = [
    r"\bif\b",
    r"\bwhen\b",
    r"\bbecause\b",
    r"\brequires\b",
    r"\bcauses\b",
    r"\buses\b",
    r"\bconsists\b",
    r"\bdefined\s+as\b",
    r"\bsuch\s+as\b",
    r"\bfor\s+example\b",
    r"\be\.g\.\b",
    r"\blike\b",
    r"\bhas\b",
    r"\bhave\b",
    r"\bincludes\b",
    r"\bcontains\b",
    r"\bmeans\b",
    r"\brefers\s+to\b",
    r"\ballows\b",
    r"\bensures\b",
    r"\bdescribes\b",
    r"\bused\s+in\b",
    r"\bused\s+for\b",
    r"\bapplied\b",
    r"\bprovides\b",
    r"\benables\b",
    r"\bworks\b",
    r"\boperates\b",
]
