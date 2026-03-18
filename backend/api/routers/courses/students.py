from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from ....db.postgres import add_user_to_course, get_conn, get_user_by_email, get_user_by_id
from ...dependencies.auth import get_current_instructor, get_current_user
from ...schemas import CourseStudentResponse, UpdateStudentAssignmentRequest
from .shared import ensure_course_access

router = APIRouter()


class AddStudentRequest(BaseModel):
    email: EmailStr
    role: Optional[str] = "student"


class AddStudentResponse(BaseModel):
    message: str
    student_id: Optional[int] = None
    student_email: str


@router.post("/{course_id}/students", response_model=AddStudentResponse, status_code=status.HTTP_201_CREATED)
async def add_student_to_course(course_id: int, request: AddStudentRequest, current_user: dict = Depends(get_current_instructor)):
    ensure_course_access(course_id, current_user)
    student = get_user_by_email(request.email)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with email {request.email} not found. Please ask the student to register first.")
    student_id, _, _, student_role, _ = student
    if student_role != "student":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User {request.email} is not a student (role: {student_role})")
    role = (request.role or "student").lower()
    if role not in ("student", "ta"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role must be student or ta")
    add_user_to_course(student_id, course_id, role)
    return AddStudentResponse(message=f"Student {request.email} successfully added to course", student_id=student_id, student_email=request.email)


@router.delete("/{course_id}/students/{student_id}", status_code=status.HTTP_200_OK)
async def remove_student_from_course(course_id: int, student_id: int, current_user: dict = Depends(get_current_instructor)):
    ensure_course_access(course_id, current_user)
    student = get_user_by_id(student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student with id {student_id} not found")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM user_courses WHERE user_id = %s AND course_id = %s", (student_id, course_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student is not enrolled in this course")
        conn.commit()
    return {"message": "Student removed from course successfully"}


@router.delete("/{course_id}/leave", status_code=status.HTTP_200_OK)
async def leave_course(course_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")
    ensure_course_access(course_id, current_user)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM user_courses WHERE user_id = %s AND course_id = %s", (current_user["id"], course_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You are not enrolled in this course")
        conn.commit()
    return {"message": "Left course successfully"}


@router.get("/{course_id}/students", response_model=List[CourseStudentResponse])
async def get_course_students(course_id: int, current_user: dict = Depends(get_current_instructor)):
    ensure_course_access(course_id, current_user)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.email, uc.role,
                   COALESCE(COUNT(CASE WHEN (l.course_id = %s OR (qh.course_id = %s AND qh.lecture_id IS NULL)) THEN qh.id END), 0) AS questions_count,
                   MAX(CASE WHEN (l.course_id = %s OR (qh.course_id = %s AND qh.lecture_id IS NULL)) THEN qh.created_at END) AS last_active
            FROM users u
            JOIN user_courses uc ON u.id = uc.user_id
            LEFT JOIN query_history qh ON qh.user_id = u.id
            LEFT JOIN lectures l ON l.id = qh.lecture_id
            WHERE uc.course_id = %s AND u.role IN ('student', 'ta')
            GROUP BY u.id, u.email, uc.role
            ORDER BY u.email
            """,
            (course_id, course_id, course_id, course_id, course_id),
        )
        students = cur.fetchall()
    return [
        CourseStudentResponse(
            student_id=row[0],
            student_email=row[1],
            role=row[2],
            questions_count=row[3] or 0,
            last_active=row[4].isoformat() if row[4] else None,
        )
        for row in students
    ]


@router.patch("/{course_id}/students/{student_id}", status_code=status.HTTP_200_OK)
async def update_student_assignment(
    course_id: int,
    student_id: int,
    payload: UpdateStudentAssignmentRequest,
    current_user: dict = Depends(get_current_instructor),
):
    ensure_course_access(course_id, current_user)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM user_courses WHERE user_id = %s AND course_id = %s", (student_id, course_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Student is not enrolled in this course")
        role = payload.role.lower() if payload.role else None
        if role and role not in ("student", "ta"):
            raise HTTPException(status_code=400, detail="Role must be student or ta")
        if role is not None:
            cur.execute("UPDATE user_courses SET role = %s WHERE user_id = %s AND course_id = %s", (role, student_id, course_id))
            conn.commit()
    return {"message": "Student updated"}
