from fastapi import HTTPException, status

from ..db.postgres import can_user_access_lecture, get_lecture
from .models import LectureResponse, QueryHistoryItem, UploadRequestResponse


def get_lecture_or_404(lecture_id: int):
    lecture = get_lecture(lecture_id)
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with id {lecture_id} not found",
        )
    return lecture


def ensure_lecture_access(lecture_id: int, current_user: dict):
    lecture = get_lecture_or_404(lecture_id)
    if not can_user_access_lecture(current_user["id"], lecture_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this lecture",
        )
    return lecture


def lecture_to_response(lecture) -> LectureResponse:
    return LectureResponse(
        id=lecture[0],
        original_name=lecture[1],
        file_path=lecture[2],
        page_count=lecture[3],
        status=lecture[4],
        created_at=lecture[5],
        course_id=lecture[6],
        file_type=lecture[7],
        has_transcript=bool(lecture[8]),
        created_by=lecture[9],
        created_by_role=lecture[10],
    )


def upload_request_to_response(row) -> UploadRequestResponse:
    return UploadRequestResponse(
        id=row[0],
        course_id=row[1],
        student_id=row[2],
        student_email=row[3],
        original_name=row[4],
        file_type=row[5],
        status=row[6],
        created_at=row[7].isoformat() if row[7] else None,
        reviewed_by=row[8],
        reviewed_at=row[9].isoformat() if row[9] else None,
    )


def query_history_item_from_row(row) -> QueryHistoryItem:
    return QueryHistoryItem(
        id=row[0],
        question=row[1],
        answer=row[2],
        created_at=row[3],
        user_email=row[4],
        page_number=row[5],
    )
