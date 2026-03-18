"""This file marks the study materials folder as a Python package.
It also exposes shared imports when this package is loaded elsewhere."""


from .key_points import generate_key_points
from .shared import LectureNotFoundError, LectureNotReadyError, get_materials
from .summary import generate_summary

__all__ = [
    "LectureNotFoundError",
    "LectureNotReadyError",
    "generate_key_points",
    "generate_summary",
    "get_materials",
]
