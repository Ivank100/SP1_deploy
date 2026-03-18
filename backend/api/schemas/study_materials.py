"""This file defines Pydantic schemas for study materials API payloads.
These models validate request bodies and keep response shapes consistent."""


from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from ...core.config import FLASHCARD_COUNT_MAX, FLASHCARD_COUNT_MIN


class SummaryResponse(BaseModel):
    lecture_id: int
    summary: str
    cached: bool = False


class KeyPointsResponse(BaseModel):
    lecture_id: int
    key_points: List[str]
    cached: bool = False


class FlashcardModel(BaseModel):
    id: int
    question: Optional[str] = None
    answer: Optional[str] = None
    front: Optional[str] = None
    back: Optional[str] = None
    page_number: Optional[int] = None
    source_keypoint_id: Optional[int] = None
    quality_score: Optional[float] = None

    def model_post_init(self, __context) -> None:
        if self.question is None and self.front:
            self.question = self.front
        if self.answer is None and self.back:
            self.answer = self.back
        if self.front is None and self.question:
            self.front = self.question
        if self.back is None and self.answer:
            self.back = self.answer

    @property
    def display_question(self) -> str:
        return self.question or self.front or ""

    @property
    def display_answer(self) -> str:
        return self.answer or self.back or ""


class FlashcardSetModel(BaseModel):
    id: int
    lecture_id: int
    strategy: str
    created_at: datetime
    created_by_user_id: Optional[int] = None

    class Config:
        from_attributes = True


class FlashcardListResponse(BaseModel):
    lecture_id: int
    flashcards: List[FlashcardModel]
    set_id: Optional[int] = None
    strategy: Optional[str] = None


class FlashcardGenerateRequest(BaseModel):
    count: int = 5
    regenerate: bool = False
    strategy: str = "keypoints_v1"

    @field_validator("count")
    @classmethod
    def count_in_range(cls, value: int) -> int:
        if not (FLASHCARD_COUNT_MIN <= value <= FLASHCARD_COUNT_MAX):
            raise ValueError(f"count must be between {FLASHCARD_COUNT_MIN} and {FLASHCARD_COUNT_MAX}")
        return value


class StudyMaterialsResponse(BaseModel):
    lecture_id: int
    summary: Optional[str] = None
    key_points: List[str]
    flashcards: List[FlashcardModel]

