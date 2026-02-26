# src/api/models.py
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# Import range from config (single source of truth)
from ..config import FLASHCARD_COUNT_MIN, FLASHCARD_COUNT_MAX

class LectureResponse(BaseModel):
    """Response model for lecture data."""
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
    """Response model for list of lectures."""
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

class CitationSource(BaseModel):
    """Structured citation metadata."""
    lecture_id: Optional[int]
    lecture_name: Optional[str]
    page_number: Optional[int] = None
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    file_type: Optional[str] = None

class QueryResponse(BaseModel):
    """Response model for query."""
    answer: str
    citation: str
    lecture_id: Optional[int] = None
    course_id: Optional[int] = None
    sources: List[CitationSource]

class UploadResponse(BaseModel):
    """Response model for file upload."""
    lecture_id: int
    message: str
    status: str

class QueryRequest(BaseModel):
    """Request model for querying a lecture."""
    question: str
    top_k: int = 5

class CourseQueryRequest(QueryRequest):
    """Request model for querying across a course."""
    pass

class QueryHistoryItem(BaseModel):
    """Response model for query history item."""
    id: int
    question: str
    answer: str
    created_at: datetime
    user_email: Optional[str] = None
    page_number: Optional[int] = None
    
    class Config:
        from_attributes = True

class QueryHistoryResponse(BaseModel):
    """Response model for query history."""
    queries: List[QueryHistoryItem]
    total: int

class SummaryResponse(BaseModel):
    """Response for lecture summary requests."""
    lecture_id: int
    summary: str
    cached: bool = False

class KeyPointsResponse(BaseModel):
    """Response for lecture key points."""
    lecture_id: int
    key_points: List[str]
    cached: bool = False

class FlashcardModel(BaseModel):
    """Single flashcard entry (supports both old and new schema)."""
    id: int
    question: Optional[str] = None
    answer: Optional[str] = None
    front: Optional[str] = None
    back: Optional[str] = None
    page_number: Optional[int] = None
    source_keypoint_id: Optional[int] = None
    quality_score: Optional[float] = None
    
    def model_post_init(self, __context) -> None:
        """Normalize front/back to question/answer for compatibility."""
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
        """Get question text (prefers question over front)."""
        return self.question or self.front or ""
    
    @property
    def display_answer(self) -> str:
        """Get answer text (prefers answer over back)."""
        return self.answer or self.back or ""

class FlashcardSetModel(BaseModel):
    """Flashcard set metadata."""
    id: int
    lecture_id: int
    strategy: str
    created_at: datetime
    created_by_user_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class FlashcardListResponse(BaseModel):
    """Response for flashcard requests."""
    lecture_id: int
    flashcards: List[FlashcardModel]
    set_id: Optional[int] = None
    strategy: Optional[str] = None

class FlashcardGenerateRequest(BaseModel):
    """Request for generating flashcards."""
    count: int = 5
    regenerate: bool = False
    strategy: str = "keypoints_v1"

    @field_validator("count")
    @classmethod
    def count_in_range(cls, v: int) -> int:
        if not (FLASHCARD_COUNT_MIN <= v <= FLASHCARD_COUNT_MAX):
            raise ValueError(f"count must be between {FLASHCARD_COUNT_MIN} and {FLASHCARD_COUNT_MAX}")
        return v

class StudyMaterialsResponse(BaseModel):
    """Aggregated study materials for a lecture."""
    lecture_id: int
    summary: Optional[str] = None
    key_points: List[str]
    flashcards: List[FlashcardModel]

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None

class CourseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    join_code: Optional[str] = None
    term_year: Optional[int] = None
    term_number: Optional[int] = None
    duration_minutes: Optional[int] = None
    lecture_count: int
    lectures: List[LectureResponse]

class CourseListResponse(BaseModel):
    """Response model for listing courses."""
    courses: List[CourseResponse]
    total: int

class CreateCourseRequest(BaseModel):
    """Request body for creating a course."""
    name: str
    description: Optional[str] = None
    term_year: Optional[int] = None
    term_number: Optional[int] = None
    duration_minutes: Optional[int] = None


class TranscriptSegment(BaseModel):
    """Single transcript segment with timestamp metadata."""
    start: float
    end: float
    text: str


class TranscriptResponse(BaseModel):
    """Response model for lecture transcripts."""
    lecture_id: int
    segments: List[TranscriptSegment]
    language: Optional[str] = None
    model: Optional[str] = None


class TranscriptionResponse(BaseModel):
    """Response for manual transcription requests."""
    lecture_id: int
    status: str
    segment_count: int
    message: str


class QueryCluster(BaseModel):
    """Single query cluster."""
    cluster_id: int
    count: int
    questions: List[str]
    representative_question: str


class QueryClustersResponse(BaseModel):
    """Response for query clustering."""
    clusters: List[QueryCluster]
    total_questions: int


class TrendPoint(BaseModel):
    """Single trend data point."""
    period: str
    count: int
    questions: List[str]


class TrendsResponse(BaseModel):
    """Response for query trends."""
    trends: List[TrendPoint]
    period: str
    days: int


class LectureHealthMetric(BaseModel):
    """Health metrics for a single lecture."""
    lecture_id: int
    lecture_name: str
    query_count: int
    avg_complexity: float
    top_clusters: List[Dict[str, Any]]


class LectureHealthResponse(BaseModel):
    """Response for lecture health metrics."""
    lectures: List[LectureHealthMetric]
    total_lectures: int


class LectureAnalyticsBin(BaseModel):
    """Single time bin for lecture question analytics."""
    start_pct: float
    end_pct: float
    start_min: Optional[int] = None
    end_min: Optional[int] = None
    count: int
    course_avg: Optional[float] = None


class LectureAnalyticsResponse(BaseModel):
    """Response for lecture-level analytics."""
    lecture_id: int
    total_questions: int
    active_students: int
    peak_confusion_range: Optional[str] = None
    top_confused_question: Optional[str] = None
    bins: List[LectureAnalyticsBin]
    course_question_total: Optional[int] = None
    course_lecture_count: Optional[int] = None


class QueryListItem(BaseModel):
    """Single query in list view."""
    id: int
    question: str
    answer: str
    lecture_id: Optional[int]
    lecture_name: Optional[str]
    created_at: Optional[str]
    user_id: Optional[int] = None
    user_email: Optional[str] = None


class QueryListResponse(BaseModel):
    """Response for query list."""
    queries: List[QueryListItem]
    total: int


class CourseStudentResponse(BaseModel):
    """Response for course student."""
    student_id: int
    student_email: str
    role: str
    section_id: Optional[int] = None
    section_name: Optional[str] = None
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    questions_count: int = 0
    last_active: Optional[str] = None


class CourseSectionResponse(BaseModel):
    id: int
    name: str


class CourseSectionListResponse(BaseModel):
    sections: List[CourseSectionResponse]


class CreateSectionRequest(BaseModel):
    name: str


class SectionGroupResponse(BaseModel):
    id: int
    name: str


class SectionGroupListResponse(BaseModel):
    groups: List[SectionGroupResponse]


class CreateGroupRequest(BaseModel):
    name: str


class UpdateStudentAssignmentRequest(BaseModel):
    role: Optional[str] = None
    section_id: Optional[int] = None
    group_id: Optional[int] = None


class CreateAnnouncementRequest(BaseModel):
    message: str


class AnnouncementResponse(BaseModel):
    id: int
    message: str
    created_by: Optional[int] = None
    created_at: Optional[str] = None


class AnnouncementListResponse(BaseModel):
    announcements: List[AnnouncementResponse]


class UploadRequestResponse(BaseModel):
    id: int
    course_id: int
    student_id: int
    student_email: Optional[str] = None
    original_name: str
    file_type: str
    status: str
    created_at: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[str] = None


class UploadRequestListResponse(BaseModel):
    requests: List[UploadRequestResponse]


class UploadRequestDecision(BaseModel):
    decision: str  # approve | reject

