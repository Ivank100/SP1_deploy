"""This file marks the rag folder as a Python package.
It also exposes shared imports when this package is loaded elsewhere."""


from .retrieval import extract_keywords
from .service import answer_question

__all__ = ["answer_question", "extract_keywords"]
