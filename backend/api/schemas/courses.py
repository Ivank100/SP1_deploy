from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from .lectures import LectureResponse


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
    courses: List[CourseResponse]
    total: int


class CreateCourseRequest(BaseModel):
    name: str
    description: Optional[str] = None
    term_year: Optional[int] = None
    term_number: Optional[int] = None
    duration_minutes: Optional[int] = None


class JoinCourseRequest(BaseModel):
    code: str


class CourseStudentResponse(BaseModel):
    student_id: int
    student_email: str
    role: str
    questions_count: int = 0
    last_active: Optional[str] = None


class UpdateStudentAssignmentRequest(BaseModel):
    role: Optional[str] = None


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
    decision: str

