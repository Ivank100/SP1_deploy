"""This file marks the flashcards folder as a Python package.
It also exposes shared imports when this package is loaded elsewhere."""


from .orchestration import generate_flashcards_v2

__all__ = ["generate_flashcards_v2"]
