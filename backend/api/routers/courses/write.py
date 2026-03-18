from fastapi import APIRouter, Depends, HTTPException, status

from ....db.postgres import assign_instructor_to_course, create_course, get_course
from ...dependencies.auth import get_current_instructor
from ...schemas import CourseResponse, CreateCourseRequest
from .shared import delete_course_and_files, get_course_or_404

router = APIRouter()


@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_new_course(
    request: CreateCourseRequest,
    current_user: dict = Depends(get_current_instructor),
):
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course name cannot be empty")
    if request.duration_minutes is not None and request.duration_minutes not in {60, 90, 120, 180}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course duration must be 60, 90, 120, or 180 minutes",
        )
    course_id = create_course(
        name=name,
        description=request.description,
        created_by=current_user["id"],
        term_year=request.term_year,
        term_number=request.term_number,
        duration_minutes=request.duration_minutes or 90,
    )
    assign_instructor_to_course(course_id, current_user["id"], assigned_by=current_user["id"])
    course = get_course(course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create course")
    return CourseResponse(
        id=course[0],
        name=course[1],
        description=course[2],
        created_at=course[3],
        join_code=course[4],
        term_year=course[5],
        term_number=course[6],
        duration_minutes=course[7],
        lecture_count=0,
        lectures=[],
    )


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course_route(course_id: int, current_user: dict = Depends(get_current_instructor)):
    get_course_or_404(course_id)
    try:
        delete_course_and_files(course_id, current_user["id"])
        return None
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
