"""This file marks the schemas folder as a Python package.
It also exposes shared imports when this package is loaded elsewhere."""


from .analytics import (
    CourseAnalyticsResponse,
    LectureAnalyticsBin,
    LectureAnalyticsResponse,
    LectureHealthMetric,
    LectureHealthResponse,
    TrendPoint,
    TrendsResponse,
)
from .auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from .common import ErrorResponse
from .courses import (
    AnnouncementListResponse,
    AnnouncementResponse,
    CourseListResponse,
    CourseResponse,
    CourseStudentResponse,
    CreateAnnouncementRequest,
    CreateCourseRequest,
    JoinCourseRequest,
    UpdateStudentAssignmentRequest,
    UploadRequestDecision,
    UploadRequestListResponse,
    UploadRequestResponse,
)
from .lectures import (
    LectureListResponse,
    LectureRenameRequest,
    LectureResource,
    LectureResourceCreateRequest,
    LectureResourceListResponse,
    LectureResponse,
    LectureStatusResponse,
    SlideListResponse,
    SlideResponse,
    TranscriptResponse,
    TranscriptSegment,
    TranscriptionResponse,
    UploadResponse,
)
from .queries import (
    CitationSource,
    CourseQueryRequest,
    QueryCluster,
    QueryClustersResponse,
    QueryHistoryItem,
    QueryHistoryResponse,
    QueryListItem,
    QueryListResponse,
    QueryRequest,
    QueryResponse,
)
from .study_materials import (
    FlashcardGenerateRequest,
    FlashcardListResponse,
    FlashcardModel,
    FlashcardSetModel,
    KeyPointsResponse,
    StudyMaterialsResponse,
    SummaryResponse,
)

