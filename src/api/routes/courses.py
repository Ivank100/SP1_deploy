from collections import defaultdict
from fastapi import APIRouter, HTTPException, UploadFile, File, status, Depends
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr

from ...db import (
    list_courses,
    list_lectures,
    get_course,
    create_course,
    can_user_access_course,
    add_user_to_course,
    assign_instructor_to_course,
    get_user_by_email,
    get_conn,
    init_schema,
    get_user_by_id,
    delete_course_as_instructor,
    enroll_student_by_code
)
from ..middleware.auth import get_current_user, get_current_instructor
from ...rag_query import answer_question
from ...analytics import get_all_queries, cluster_questions, get_query_trends
from ..models import (
    CourseListResponse,
    CourseResponse,
    CreateCourseRequest,
    LectureResponse,
    UploadResponse,
    QueryResponse,
    CourseQueryRequest,
)
from .lectures import process_lecture_upload

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("", response_model=CourseListResponse)
async def list_all_courses(current_user: dict = Depends(get_current_user)):
    """Return all courses along with their lectures (filtered by user access)."""
    courses = list_courses()
    lectures = list_lectures()
    
    # Filter courses based on user role and enrollment
    if current_user["role"] == "student":
        # Students only see courses they're enrolled in
        from ...db import get_user_courses
        user_course_ids = get_user_courses(current_user["id"])
        courses = [c for c in courses if c[0] in user_course_ids]
        lectures = [l for l in lectures if l[6] in user_course_ids]
    elif current_user["role"] == "instructor":
        # Instructors see courses they're assigned to (or all if no assignments exist)
        init_schema()
        with get_conn() as conn, conn.cursor() as cur:
            # Check if any assignments exist
            cur.execute("SELECT COUNT(*) FROM course_instructors")
            has_assignments = cur.fetchone()[0] > 0
            
            if has_assignments:
                # Only show assigned courses
                cur.execute(
                    """
                    SELECT course_id FROM course_instructors
                    WHERE instructor_id = %s
                    """,
                    (current_user["id"],),
                )
                assigned_course_ids = [row[0] for row in cur.fetchall()]
                # Also check courses created by instructor
                cur.execute(
                    """
                    SELECT id FROM courses WHERE created_by = %s
                    """,
                    (current_user["id"],),
                )
                created_course_ids = [row[0] for row in cur.fetchall()]
                all_course_ids = list(set(assigned_course_ids + created_course_ids))
                courses = [c for c in courses if c[0] in all_course_ids]
                lectures = [l for l in lectures if l[6] in all_course_ids]

    lectures_by_course = defaultdict(list)
    for lect in lectures:
        lectures_by_course[lect[6]].append(lect)

    course_responses = []
    for course in courses:
        course_id = course[0]
        course_lectures = [
            LectureResponse(
                id=lect[0],
                original_name=lect[1],
                file_path=lect[2],
                page_count=lect[3],
                status=lect[4],
                created_at=lect[5],
                course_id=lect[6],
                file_type=lect[7],
                has_transcript=lect[8],
            )
            for lect in lectures_by_course.get(course_id, [])
        ]
        course_responses.append(
            CourseResponse(
                id=course_id,
                name=course[1],
                description=course[2],
                created_at=course[3],
                join_code=course[4], # <--- Add this (ensure index 4 matches your db.py select)
                lecture_count=len(course_lectures),
                lectures=course_lectures,
            )
        )

    return CourseListResponse(courses=course_responses, total=len(course_responses))


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_new_course(
    request: CreateCourseRequest,
    current_user: dict = Depends(get_current_instructor),
):
    """Create a new course. Only instructors can create courses."""
    name = request.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course name cannot be empty",
        )

    course_id = create_course(name=name, description=request.description, created_by=current_user["id"])
    
    # Automatically assign instructor to the course they created
    assign_instructor_to_course(course_id, current_user["id"], assigned_by=current_user["id"])
    course = get_course(course_id)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create course",
        )

    return CourseResponse(
        id=course[0],
        name=course[1],
        description=course[2],
        created_at=course[3],
        join_code=course[4], # <--- Add this line
        lecture_count=0,
        lectures=[],
    )


@router.post(
    "/{course_id}/lectures",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_lecture_to_course(
    course_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a lecture into a specific course."""
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )
    
    # Check access
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this course",
        )

    return await process_lecture_upload(file, course_id=course_id, created_by=current_user["id"])


@router.post("/{course_id}/query", response_model=QueryResponse)
async def query_course(
    course_id: int,
    request: CourseQueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """Ask a question across all lectures in a course. Only students can ask questions."""
    # Only students can ask questions
    if current_user["role"] != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can ask questions",
        )
    
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )
    
    # Check access
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this course",
        )

    lectures = list_lectures(course_id=course_id)
    completed = [lect for lect in lectures if lect[4] == "completed"]
    if not completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course has no completed lectures to search across",
        )

    answer, citation, sources = answer_question(
        question=request.question,
        course_id=course_id,
        top_k=request.top_k,
        user_id=current_user["id"]
    )

    return QueryResponse(
        answer=answer,
        citation=citation,
        lecture_id=None,
        course_id=course_id,
        sources=sources,
    )


class AddStudentRequest(BaseModel):
    """Request to add a student to a course by email."""
    email: EmailStr


class AddStudentResponse(BaseModel):
    """Response for adding a student."""
    message: str
    student_id: Optional[int] = None
    student_email: str


class CourseAnalyticsResponse(BaseModel):
    """Course analytics overview."""
    total_questions: int
    active_students: int
    top_confused_topics: List[Dict[str, Any]]
    trend_percentage: float
    trend_direction: str  # "up" or "down"


@router.get("/{course_id}/analytics", response_model=CourseAnalyticsResponse)
async def get_course_analytics(
    course_id: int,
    current_user: dict = Depends(get_current_instructor),
):
    """Get course-level analytics overview. Only instructors can access this."""
    # Check if course exists
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )
    
    # Check if instructor has access to this course
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this course",
        )
    
    # Get all queries for this course
    queries = get_all_queries(limit=1000, course_id=course_id)
    total_questions = len(queries)
    
    # Get unique active students
    active_students = len(set(q["user_id"] for q in queries if q.get("user_id")))
    
    # Get top confused topics (clusters)
    questions = [q["question"] for q in queries if q.get("question")]
    clusters = cluster_questions(questions, n_clusters=5) if questions else []
    top_confused_topics = [
        {
            "topic": c["representative_question"],
            "count": c["count"],
            "questions": c.get("questions", [])[:3],
        }
        for c in clusters[:5]
    ]
    
    # Calculate trend (last 7 days vs previous 7 days)
    from datetime import datetime, timedelta
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        now = datetime.now()
        last_7_days = now - timedelta(days=7)
        previous_7_days = last_7_days - timedelta(days=7)
        
        # Count queries in last 7 days
        cur.execute(
            """
            SELECT COUNT(*) FROM query_history qh
            LEFT JOIN lectures l ON qh.lecture_id = l.id
            WHERE (l.course_id = %s OR (qh.course_id = %s AND qh.lecture_id IS NULL))
            AND qh.created_at >= %s
            """,
            (course_id, course_id, last_7_days),
        )
        recent_count = cur.fetchone()[0]
        
        # Count queries in previous 7 days
        cur.execute(
            """
            SELECT COUNT(*) FROM query_history qh
            LEFT JOIN lectures l ON qh.lecture_id = l.id
            WHERE (l.course_id = %s OR (qh.course_id = %s AND qh.lecture_id IS NULL))
            AND qh.created_at >= %s AND qh.created_at < %s
            """,
            (course_id, course_id, previous_7_days, last_7_days),
        )
        previous_count = cur.fetchone()[0]
        
        # Calculate trend percentage
        if previous_count > 0:
            trend_percentage = ((recent_count - previous_count) / previous_count) * 100
            trend_direction = "up" if recent_count > previous_count else "down"
        elif recent_count > 0:
            trend_percentage = 100.0
            trend_direction = "up"
        else:
            trend_percentage = 0.0
            trend_direction = "stable"
    
    return CourseAnalyticsResponse(
        total_questions=total_questions,
        active_students=active_students,
        top_confused_topics=top_confused_topics,
        trend_percentage=round(abs(trend_percentage), 1),
        trend_direction=trend_direction,
    )


@router.post("/{course_id}/students", response_model=AddStudentResponse, status_code=status.HTTP_201_CREATED)
async def add_student_to_course(
    course_id: int,
    request: AddStudentRequest,
    current_user: dict = Depends(get_current_instructor),
):
    """
    Add a student to a course by email. Only instructors can add students.
    If the student doesn't exist, they will need to register first.
    """
    # Check if course exists
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )
    
    # Check if instructor has access to this course
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this course",
        )
    
    # Find user by email
    student = get_user_by_email(request.email)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {request.email} not found. Please ask the student to register first.",
        )
    
    student_id, _, _, student_role, _ = student
    
    # Verify they're a student
    if student_role != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {request.email} is not a student (role: {student_role})",
        )
    
    # Add student to course
    try:
        add_user_to_course(student_id, course_id)
        return AddStudentResponse(
            message=f"Student {request.email} successfully added to course",
            student_id=student_id,
            student_email=request.email,
        )
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Student {request.email} is already enrolled in this course",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{course_id}/students/{student_id}", status_code=status.HTTP_200_OK)
async def remove_student_from_course(
    course_id: int,
    student_id: int,
    current_user: dict = Depends(get_current_instructor),
):
    """
    Remove a student from a course. Only instructors can remove students.
    """
    # Check if course exists
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )
    
    # Check if instructor has access to this course
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this course",
        )
    
    # Verify student exists
    student = get_user_by_id(student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id {student_id} not found",
        )
    
    # Remove student from course
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM user_courses
            WHERE user_id = %s AND course_id = %s
            """,
            (student_id, course_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student is not enrolled in this course",
            )
        conn.commit()
    
    return {"message": f"Student removed from course successfully"}


class CourseStudentResponse(BaseModel):
    """Response for course student."""
    student_id: int
    student_email: str


@router.get("/{course_id}/students", response_model=List[CourseStudentResponse])
async def get_course_students(
    course_id: int,
    current_user: dict = Depends(get_current_instructor),
):
    """
    Get all students enrolled in a course. Only instructors can view this.
    """
    # Check if course exists
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )
    
    # Check if instructor has access to this course
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this course",
        )
    
    # Get all students enrolled in the course
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.email
            FROM users u
            JOIN user_courses uc ON u.id = uc.user_id
            WHERE uc.course_id = %s AND u.role = 'student'
            ORDER BY u.email
            """,
            (course_id,),
        )
        students = cur.fetchall()
    
    return [
        CourseStudentResponse(student_id=row[0], student_email=row[1])
        for row in students
    ]

@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course_route(
    course_id: int, 
    current_user: dict = Depends(get_current_instructor)
):
    course = get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    try:
        # Get lectures to identify files for deletion
        lectures = list_lectures(course_id=course_id)
        
        # Call the DB function from your src/db.py
        delete_course_as_instructor(course_id, current_user["id"])
        
        # Clean up files (Works on Windows & Linux)
        import os
        for lect in lectures:
            file_path = lect[2] 
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass 
        return None
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
@router.post("/join", status_code=200)
async def join_course_by_code(
    payload: dict, 
    current_user: dict = Depends(get_current_user)
):
    """Endpoint for students to join a course using a code."""
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Join code is required")
    
    try:
        # Call the function we just added to db.py
        course_id = enroll_student_by_code(current_user["id"], code)
        return {"message": "Successfully joined course", "course_id": course_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))