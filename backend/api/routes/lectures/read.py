from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ...middleware.auth import get_current_instructor, get_current_user
from ...models import LectureAnalyticsResponse, LectureListResponse, LectureResponse
from .shared import ensure_lecture_access, get_instructor_visible_course_ids, get_user_courses, get_lecture_analytics, get_lecture_or_404, lecture_to_response, list_lectures

router = APIRouter()


@router.get("/", response_model=LectureListResponse)
async def list_all_lectures(course_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    lectures = list_lectures(course_id=course_id)
    if current_user["role"] == "student":
        user_course_ids = get_user_courses(current_user["id"])
        lectures = [l for l in lectures if l[6] in user_course_ids]
    elif current_user["role"] == "instructor":
        visible_course_ids = get_instructor_visible_course_ids(current_user["id"])
        if visible_course_ids is not None:
            lectures = [l for l in lectures if l[6] in visible_course_ids]
    lecture_responses = [lecture_to_response(lect) for lect in lectures]
    return LectureListResponse(lectures=lecture_responses, total=len(lecture_responses))


@router.get("/{lecture_id}/analytics", response_model=LectureAnalyticsResponse)
async def get_lecture_analytics_route(lecture_id: int, current_user: dict = Depends(get_current_instructor)):
    lecture = ensure_lecture_access(lecture_id, current_user)
    data = get_lecture_analytics(lecture_id=lecture_id, course_id=lecture[6])
    return LectureAnalyticsResponse(**data)


@router.get("/{lecture_id}", response_model=LectureResponse)
async def get_lecture_by_id(lecture_id: int, current_user: dict = Depends(get_current_user)):
    lecture = ensure_lecture_access(lecture_id, current_user)
    return lecture_to_response(lecture)


@router.get("/{lecture_id}/status", response_model=dict)
async def get_lecture_status(lecture_id: int):
    lecture = get_lecture_or_404(lecture_id)
    return {
        "lecture_id": lecture_id,
        "status": lecture[4],
        "page_count": lecture[3],
        "course_id": lecture[6],
        "file_type": lecture[7],
        "has_transcript": bool(lecture[8]),
    }


@router.get("/{lecture_id}/download")
async def download_lecture_file(lecture_id: int, current_user: dict = Depends(get_current_user)):
    lecture = ensure_lecture_access(lecture_id, current_user)
    file_path = lecture[2]
    original_name = lecture[1] or "lecture"
    if not file_path:
        raise HTTPException(status_code=404, detail="No file associated with this lecture")
    full_path = Path(file_path).resolve()
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    return FileResponse(path=str(full_path), filename=original_name, media_type="application/octet-stream")
