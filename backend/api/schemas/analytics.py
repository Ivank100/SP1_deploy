"""This file defines Pydantic schemas for analytics API payloads.
These models validate request bodies and keep response shapes consistent."""


from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TrendPoint(BaseModel):
    period: str
    count: int
    questions: List[str]


class TrendsResponse(BaseModel):
    trends: List[TrendPoint]
    period: str
    days: int


class LectureHealthMetric(BaseModel):
    lecture_id: int
    lecture_name: str
    query_count: int
    avg_complexity: float
    top_clusters: List[Dict[str, Any]]


class LectureHealthResponse(BaseModel):
    lectures: List[LectureHealthMetric]
    total_lectures: int


class LectureAnalyticsBin(BaseModel):
    start_pct: float
    end_pct: float
    start_min: Optional[int] = None
    end_min: Optional[int] = None
    count: int
    course_avg: Optional[float] = None


class LectureAnalyticsResponse(BaseModel):
    lecture_id: int
    total_questions: int
    active_students: int
    peak_confusion_range: Optional[str] = None
    top_confused_question: Optional[str] = None
    bins: List[LectureAnalyticsBin]
    course_question_total: Optional[int] = None
    course_lecture_count: Optional[int] = None


class CourseAnalyticsResponse(BaseModel):
    total_questions: int
    active_students: int
    top_confused_topics: List[Dict[str, Any]]
    trend_percentage: float
    trend_direction: str

