"""This file defines Pydantic schemas for queries API payloads.
These models validate request bodies and keep response shapes consistent."""


from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CitationSource(BaseModel):
    lecture_id: Optional[int]
    lecture_name: Optional[str]
    page_number: Optional[int] = None
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    file_type: Optional[str] = None


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    query_mode: Optional[str] = None


class CourseQueryRequest(QueryRequest):
    pass


class QueryResponse(BaseModel):
    answer: str
    citation: str
    lecture_id: Optional[int] = None
    course_id: Optional[int] = None
    sources: List[CitationSource]


class QueryHistoryItem(BaseModel):
    id: int
    question: str
    answer: str
    created_at: datetime
    user_email: Optional[str] = None
    page_number: Optional[int] = None

    class Config:
        from_attributes = True


class QueryHistoryResponse(BaseModel):
    queries: List[QueryHistoryItem]
    total: int


class QueryCluster(BaseModel):
    cluster_id: int
    count: int
    questions: List[str]
    representative_question: str


class QueryClustersResponse(BaseModel):
    clusters: List[QueryCluster]
    total_questions: int


class QueryListItem(BaseModel):
    id: int
    question: str
    answer: str
    lecture_id: Optional[int]
    lecture_name: Optional[str]
    created_at: Optional[str]
    user_id: Optional[int] = None
    user_email: Optional[str] = None


class QueryListResponse(BaseModel):
    queries: List[QueryListItem]
    total: int

