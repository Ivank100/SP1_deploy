from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class LectureResponse(BaseModel):
    id: int
    original_name: str
    file_path: str
    page_count: int
    status: str
    created_at: datetime
    course_id: Optional[int] = None
    file_type: str
    has_transcript: bool = False
    created_by: Optional[int] = None
    created_by_role: Optional[str] = None

    class Config:
        from_attributes = True


class LectureListResponse(BaseModel):
    lectures: List[LectureResponse]
    total: int


class LectureRenameRequest(BaseModel):
    name: str


class LectureResource(BaseModel):
    id: int
    lecture_id: int
    title: str
    url: str
    created_at: datetime

    class Config:
        from_attributes = True


class LectureResourceCreateRequest(BaseModel):
    title: str
    url: str


class LectureResourceListResponse(BaseModel):
    resources: List[LectureResource]


class UploadResponse(BaseModel):
    lecture_id: int
    message: str
    status: str


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptResponse(BaseModel):
    lecture_id: int
    segments: List[TranscriptSegment]
    language: Optional[str] = None
    model: Optional[str] = None


class TranscriptionResponse(BaseModel):
    lecture_id: int
    status: str
    segment_count: int
    message: str


class SlideResponse(BaseModel):
    slide_number: int
    text: str


class SlideListResponse(BaseModel):
    lecture_id: int
    slides: List[SlideResponse]
    total: int


class LectureStatusResponse(BaseModel):
    lecture_id: int
    status: str
    page_count: int
    course_id: Optional[int] = None
    file_type: str
    has_transcript: bool = False

