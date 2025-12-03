# src/api/models.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

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

    class Config:
        from_attributes = True

class LectureListResponse(BaseModel):
    """Response model for list of lectures."""
    lectures: List[LectureResponse]
    total: int

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
    """Single flashcard entry."""
    id: int
    front: str
    back: str
    page_number: Optional[int] = None

class FlashcardListResponse(BaseModel):
    """Response for flashcard requests."""
    lecture_id: int
    flashcards: List[FlashcardModel]

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
    """Response model for course data."""
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    lecture_count: int = 0
    lectures: List[LectureResponse] = []

class CourseListResponse(BaseModel):
    """Response model for listing courses."""
    courses: List[CourseResponse]
    total: int

class CreateCourseRequest(BaseModel):
    """Request body for creating a course."""
    name: str
    description: Optional[str] = None


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

