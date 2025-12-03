# src/api/routes/admin.py
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Optional

from ...db import (
    get_course,
    list_courses,
    get_user_by_id,
    get_user_by_email,
    list_lectures,
)
from ..middleware.auth import get_current_admin
from ..models import ErrorResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AssignInstructorRequest(BaseModel):
    course_id: int
    instructor_email: str


class CourseInstructorResponse(BaseModel):
    course_id: int
    course_name: str
    instructor_id: int
    instructor_email: str
    assigned_at: str


class CourseInstructorsResponse(BaseModel):
    course_id: int
    course_name: str
    instructors: List[dict]


def assign_instructor_to_course(course_id: int, instructor_id: int, assigned_by: int):
    """Assign an instructor to a course."""
    from ...db import get_conn, init_schema
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO course_instructors (course_id, instructor_id, assigned_by)
                VALUES (%s, %s, %s)
                ON CONFLICT (course_id, instructor_id) DO NOTHING
                RETURNING assigned_at
                """,
                (course_id, instructor_id, assigned_by),
            )
            result = cur.fetchone()
            conn.commit()
            return result[0] if result else None
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Failed to assign instructor: {str(e)}")


def get_course_instructors(course_id: int) -> List[dict]:
    """Get all instructors assigned to a course."""
    from ...db import get_conn, init_schema
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT 
                ci.instructor_id,
                u.email,
                ci.assigned_at,
                ci.assigned_by
            FROM course_instructors ci
            JOIN users u ON ci.instructor_id = u.id
            WHERE ci.course_id = %s
            ORDER BY ci.assigned_at DESC
            """,
            (course_id,),
        )
        return [
            {
                "instructor_id": row[0],
                "instructor_email": row[1],
                "assigned_at": row[2].isoformat() if row[2] else None,
                "assigned_by": row[2],
            }
            for row in cur.fetchall()
        ]


@router.post("/courses/{course_id}/instructors", response_model=CourseInstructorResponse)
async def assign_instructor(
    course_id: int,
    request: AssignInstructorRequest,
    current_user: dict = Depends(get_current_admin),
):
    """Assign an instructor to a course."""
    # Verify course exists
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )
    
    # Verify instructor exists and is an instructor
    instructor = get_user_by_email(request.instructor_email)
    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instructor with email {request.instructor_email} not found",
        )
    
    instructor_id, email, _, role, _ = instructor
    if role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {email} is not an instructor",
        )
    
    # Assign instructor
    try:
        assigned_at = assign_instructor_to_course(course_id, instructor_id, current_user["id"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return CourseInstructorResponse(
        course_id=course_id,
        course_name=course[1],
        instructor_id=instructor_id,
        instructor_email=email,
        assigned_at=assigned_at.isoformat() if assigned_at else "",
    )


@router.get("/courses/{course_id}/instructors", response_model=CourseInstructorsResponse)
async def get_course_instructors_list(
    course_id: int,
    current_user: dict = Depends(get_current_admin),
):
    """Get all instructors assigned to a course."""
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )
    
    instructors = get_course_instructors(course_id)
    
    return CourseInstructorsResponse(
        course_id=course_id,
        course_name=course[1],
        instructors=instructors,
    )


@router.delete("/courses/{course_id}/instructors/{instructor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_instructor(
    course_id: int,
    instructor_id: int,
    current_user: dict = Depends(get_current_admin),
):
    """Remove an instructor from a course."""
    from ...db import get_conn, init_schema
    init_schema()
    
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )
    
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM course_instructors
            WHERE course_id = %s AND instructor_id = %s
            """,
            (course_id, instructor_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instructor assignment not found",
            )
        conn.commit()

