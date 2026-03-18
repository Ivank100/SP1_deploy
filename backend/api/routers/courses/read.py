"""This file defines read-only course endpoints.
It returns course lists, details, and membership-aware views for the frontend."""


from fastapi import APIRouter, Depends, HTTPException, status

from ....db.postgres import enroll_student_by_code
from ....services.rag import answer_question
from ...dependencies.auth import get_current_instructor, get_current_user
from ...schemas import CourseListResponse, CourseQueryRequest, JoinCourseRequest, QueryResponse
from .shared import build_course_list_response, ensure_course_access

router = APIRouter()


@router.get("/", response_model=CourseListResponse)
async def list_all_courses(current_user: dict = Depends(get_current_user)):
    course_responses = build_course_list_response(current_user)
    return CourseListResponse(courses=course_responses, total=len(course_responses))


@router.post("/{course_id}/query", response_model=QueryResponse)
async def query_course(
    course_id: int,
    request: CourseQueryRequest,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can ask questions")
    ensure_course_access(course_id, current_user)
    answer, citation, sources = answer_question(
        question=request.question,
        course_id=course_id,
        top_k=request.top_k,
        user_id=current_user["id"],
    )
    return QueryResponse(answer=answer, citation=citation, lecture_id=None, course_id=course_id, sources=sources)


@router.post("/join", status_code=200)
async def join_course_by_code(payload: JoinCourseRequest, current_user: dict = Depends(get_current_user)):
    code = payload.code
    if not code:
        raise HTTPException(status_code=400, detail="Join code is required")
    try:
        course_id = enroll_student_by_code(current_user["id"], code)
        return {"message": "Successfully joined course", "course_id": course_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
