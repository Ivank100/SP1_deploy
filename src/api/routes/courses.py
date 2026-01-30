from collections import defaultdict
import os
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, HTTPException, UploadFile, File, status, Depends
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr

from ...config import UPLOAD_DIR
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
    enroll_student_by_code,
    get_user_courses,
    get_or_create_default_section,
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
    CourseStudentResponse,
    CourseSectionListResponse,
    CourseSectionResponse,
    CreateSectionRequest,
    SectionGroupListResponse,
    SectionGroupResponse,
    CreateGroupRequest,
    UpdateStudentAssignmentRequest,
    CreateAnnouncementRequest,
    AnnouncementListResponse,
    AnnouncementResponse,
    UploadRequestResponse,
    UploadRequestListResponse,
)
from .lectures import process_lecture_upload
from ...rag_index import ingest_pdf, ingest_audio, ingest_slides

router = APIRouter(prefix="/api/courses", tags=["courses"])

# Upload validation (reuse same extensions as lecture uploads)
MAX_FILE_SIZE = 50 * 1024 * 1024
PDF_EXTENSIONS = {".pdf"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
SLIDE_EXTENSIONS = {".pptx", ".ppt"}
ALLOWED_EXTENSIONS = PDF_EXTENSIONS | AUDIO_EXTENSIONS | SLIDE_EXTENSIONS


def _file_type_from_extension(file_ext: str) -> Optional[str]:
    if file_ext in PDF_EXTENSIONS:
        return "pdf"
    if file_ext in AUDIO_EXTENSIONS:
        return "audio"
    if file_ext in SLIDE_EXTENSIONS:
        return "slides"
    return None


def _is_ta_for_course(user_id: int, course_id: int) -> bool:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT role FROM user_courses WHERE user_id = %s AND course_id = %s",
            (user_id, course_id),
        )
        row = cur.fetchone()
        return bool(row and row[0] == "ta")


@router.get("", response_model=CourseListResponse)
async def list_all_courses(current_user: dict = Depends(get_current_user)):
    """Return all courses along with their lectures (filtered by user access)."""
    courses = list_courses()
    lectures = list_lectures()
    
    # Filter courses based on user role and enrollment
    if current_user["role"] == "student":
        # Students only see courses they're enrolled in (user_courses table)
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
                created_by=lect[9],
                created_by_role=lect[10],
            )
            for lect in lectures_by_course.get(course_id, [])
        ]
        course_responses.append(
            CourseResponse(
                id=course_id,
                name=course[1],
                description=course[2],
                created_at=course[3],
                join_code=course[4],
                term_year=course[5],
                term_number=course[6],
                duration_minutes=course[7],
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
        join_code=course[4],
        term_year=course[5],
        term_number=course[6],
        duration_minutes=course[7],
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

    # Students must request approval unless they are TA
    if current_user["role"] == "student" and not _is_ta_for_course(current_user["id"], course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students must request upload approval from instructor",
        )

    return await process_lecture_upload(file, course_id=course_id, created_by=current_user["id"])


@router.post(
    "/{course_id}/upload-requests",
    response_model=UploadRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_upload_request(
    course_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Students submit an upload request; instructors/TAs can upload directly."""
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )

    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this course",
        )

    if current_user["role"] == "student" and _is_ta_for_course(current_user["id"], course_id):
        # TA can upload directly
        await process_lecture_upload(file, course_id=course_id, created_by=current_user["id"])
        return UploadRequestResponse(
            id=0,
            course_id=course_id,
            student_id=current_user["id"],
            student_email=current_user["email"],
            original_name=file.filename or "upload",
            file_type="direct",
            status="approved",
        )

    if current_user["role"] != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use direct upload for instructors",
        )

    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed: PDF, MP3, WAV, M4A, PPT, PPTX.",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB",
        )

    file_type = _file_type_from_extension(file_ext)
    if not file_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type",
        )

    pending_dir = os.path.join(UPLOAD_DIR, "pending")
    os.makedirs(pending_dir, exist_ok=True)
    safe_name = f"{uuid4().hex}{file_ext}"
    pending_path = os.path.join(pending_dir, safe_name)
    with open(pending_path, "wb") as handle:
        handle.write(contents)

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO lecture_upload_requests (course_id, student_id, original_name, file_path, file_type, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
            RETURNING id, created_at
            """,
            (course_id, current_user["id"], file.filename or "upload", pending_path, file_type),
        )
        row = cur.fetchone()
        conn.commit()

    return UploadRequestResponse(
        id=row[0],
        course_id=course_id,
        student_id=current_user["id"],
        student_email=current_user["email"],
        original_name=file.filename or "upload",
        file_type=file_type,
        status="pending",
        created_at=row[1].isoformat() if row[1] else None,
    )


@router.get("/{course_id}/upload-requests", response_model=UploadRequestListResponse)
async def list_upload_requests(
    course_id: int,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """List upload requests (instructor/TA only)."""
    if current_user["role"] != "instructor" and not _is_ta_for_course(current_user["id"], course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor or TA access required",
        )

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        base_query = """
            SELECT r.id, r.course_id, r.student_id, u.email, r.original_name, r.file_type, r.status,
                   r.created_at, r.reviewed_by, r.reviewed_at
            FROM lecture_upload_requests r
            JOIN users u ON u.id = r.student_id
            WHERE r.course_id = %s
        """
        params: List[Any] = [course_id]
        if status:
            base_query += " AND r.status = %s"
            params.append(status)
        base_query += " ORDER BY r.created_at DESC"
        cur.execute(base_query, tuple(params))
        rows = cur.fetchall()

    return UploadRequestListResponse(
        requests=[
            UploadRequestResponse(
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
            for row in rows
        ]
    )


@router.get("/{course_id}/upload-requests/mine", response_model=UploadRequestListResponse)
async def list_my_upload_requests(
    course_id: int,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """List current student's own upload requests."""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Student access required")

    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        base_query = """
            SELECT r.id, r.course_id, r.student_id, u.email, r.original_name, r.file_type, r.status,
                   r.created_at, r.reviewed_by, r.reviewed_at
            FROM lecture_upload_requests r
            JOIN users u ON u.id = r.student_id
            WHERE r.course_id = %s AND r.student_id = %s
        """
        params: List[Any] = [course_id, current_user["id"]]
        if status:
            base_query += " AND r.status = %s"
            params.append(status)
        base_query += " ORDER BY r.created_at DESC"
        cur.execute(base_query, tuple(params))
        rows = cur.fetchall()

    return UploadRequestListResponse(
        requests=[
            UploadRequestResponse(
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
            for row in rows
        ]
    )


@router.post("/{course_id}/upload-requests/{request_id}/approve", response_model=UploadResponse)
async def approve_upload_request(
    course_id: int,
    request_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Approve and ingest an upload request."""
    if current_user["role"] != "instructor" and not _is_ta_for_course(current_user["id"], course_id):
        raise HTTPException(status_code=403, detail="Instructor or TA access required")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, student_id, original_name, file_path, file_type, status
            FROM lecture_upload_requests
            WHERE id = %s AND course_id = %s
            """,
            (request_id, course_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Upload request not found")
        if row[5] != "pending":
            raise HTTPException(status_code=400, detail="Upload request already processed")

    request_id, student_id, original_name, file_path, file_type, _ = row
    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Pending file not found")

    if file_type == "pdf":
        lecture_id = ingest_pdf(file_path, original_name=original_name, course_id=course_id, created_by=student_id)
    elif file_type == "audio":
        lecture_id = ingest_audio(file_path, original_name=original_name, course_id=course_id, created_by=student_id)
    else:
        lecture_id = ingest_slides(file_path, original_name=original_name, course_id=course_id, created_by=student_id)

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE lecture_upload_requests
            SET status = 'approved', reviewed_by = %s, reviewed_at = NOW()
            WHERE id = %s
            """,
            (current_user["id"], request_id),
        )
        conn.commit()

    try:
        os.remove(file_path)
    except OSError:
        pass

    return UploadResponse(
        lecture_id=lecture_id,
        message="Upload approved and processed successfully",
        status="completed",
    )


@router.post("/{course_id}/upload-requests/{request_id}/reject", status_code=status.HTTP_200_OK)
async def reject_upload_request(
    course_id: int,
    request_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Reject an upload request."""
    if current_user["role"] != "instructor" and not _is_ta_for_course(current_user["id"], course_id):
        raise HTTPException(status_code=403, detail="Instructor or TA access required")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT file_path, status
            FROM lecture_upload_requests
            WHERE id = %s AND course_id = %s
            """,
            (request_id, course_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Upload request not found")
        if row[1] != "pending":
            raise HTTPException(status_code=400, detail="Upload request already processed")

        cur.execute(
            """
            UPDATE lecture_upload_requests
            SET status = 'rejected', reviewed_by = %s, reviewed_at = NOW()
            WHERE id = %s
            """,
            (current_user["id"], request_id),
        )
        conn.commit()

    file_path = row[0]
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    return {"message": "Upload request rejected"}


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
    section_id: Optional[int] = None
    group_id: Optional[int] = None
    role: Optional[str] = "student"


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
    
    role = (request.role or "student").lower()
    if role not in ("student", "ta"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be student or ta",
        )

    # Ensure section exists (required)
    section_id = request.section_id or get_or_create_default_section(course_id)

    # Validate section belongs to course
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM course_sections WHERE id = %s AND course_id = %s",
            (section_id, course_id),
        )
        if not cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected section does not belong to this course",
            )

        group_id = request.group_id
        if group_id is not None:
            cur.execute(
                "SELECT 1 FROM section_groups WHERE id = %s AND section_id = %s",
                (group_id, section_id),
            )
            if not cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected group does not belong to this section",
                )

    # Add student to course (insert into user_courses so they see it on their dashboard)
    try:
        add_user_to_course(student_id, course_id, role, section_id=section_id, group_id=request.group_id)
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


@router.delete("/{course_id}/leave", status_code=status.HTTP_200_OK)
async def leave_course(
    course_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    Allow a student to leave a course they are enrolled in.
    """
    if current_user["role"] != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required",
        )

    # Check if course exists
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM user_courses
            WHERE user_id = %s AND course_id = %s
            """,
            (current_user["id"], course_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You are not enrolled in this course",
            )
        conn.commit()

    return {"message": "Left course successfully"}


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
    
    # Get all students enrolled in the course with section/group/activity
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.id,
                   u.email,
                   uc.role,
                   uc.section_id,
                   s.name AS section_name,
                   uc.group_id,
                   g.name AS group_name,
                   COALESCE(COUNT(CASE WHEN (l.course_id = %s OR (qh.course_id = %s AND qh.lecture_id IS NULL)) THEN qh.id END), 0) AS questions_count,
                   MAX(CASE WHEN (l.course_id = %s OR (qh.course_id = %s AND qh.lecture_id IS NULL)) THEN qh.created_at END) AS last_active
            FROM users u
            JOIN user_courses uc ON u.id = uc.user_id
            LEFT JOIN course_sections s ON s.id = uc.section_id
            LEFT JOIN section_groups g ON g.id = uc.group_id
            LEFT JOIN query_history qh
              ON qh.user_id = u.id
            LEFT JOIN lectures l ON l.id = qh.lecture_id
            WHERE uc.course_id = %s AND u.role IN ('student', 'ta')
            GROUP BY u.id, u.email, uc.role, uc.section_id, s.name, uc.group_id, g.name
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
            section_id=row[3],
            section_name=row[4],
            group_id=row[5],
            group_name=row[6],
            questions_count=row[7] or 0,
            last_active=row[8].isoformat() if row[8] else None,
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
    """Update student role/section/group within a course."""
    # Check course access
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        # Validate student enrollment
        cur.execute(
            "SELECT 1 FROM user_courses WHERE user_id = %s AND course_id = %s",
            (student_id, course_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Student is not enrolled in this course")

        role = payload.role.lower() if payload.role else None
        fields_set = payload.model_fields_set
        role_provided = "role" in fields_set
        section_provided = "section_id" in fields_set
        group_provided = "group_id" in fields_set
        if role and role not in ("student", "ta"):
            raise HTTPException(status_code=400, detail="Role must be student or ta")

        section_id = payload.section_id
        group_id = payload.group_id

        if section_provided and section_id is not None:
            cur.execute(
                "SELECT 1 FROM course_sections WHERE id = %s AND course_id = %s",
                (section_id, course_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=400, detail="Selected section does not belong to this course")

        if group_provided and group_id is not None:
            cur.execute(
                "SELECT 1 FROM section_groups WHERE id = %s",
                (group_id,),
            )
            group = cur.fetchone()
            if not group:
                raise HTTPException(status_code=400, detail="Selected group does not exist")

            if section_provided and section_id is not None:
                cur.execute(
                    "SELECT 1 FROM section_groups WHERE id = %s AND section_id = %s",
                    (group_id, section_id),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=400, detail="Selected group does not belong to this section")

        cur.execute(
            """
            UPDATE user_courses
            SET role = CASE WHEN %s THEN COALESCE(%s, role) ELSE role END,
                section_id = CASE WHEN %s THEN %s ELSE section_id END,
                group_id = CASE WHEN %s THEN %s ELSE group_id END
            WHERE user_id = %s AND course_id = %s
            """,
            (
                role_provided,
                role,
                section_provided,
                section_id,
                group_provided,
                group_id,
                student_id,
                course_id,
            ),
        )
        conn.commit()

    return {"message": "Student updated"}


@router.get("/{course_id}/sections", response_model=CourseSectionListResponse)
async def list_sections(
    course_id: int,
    current_user: dict = Depends(get_current_instructor),
):
    """List sections for a course."""
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, name FROM course_sections WHERE course_id = %s ORDER BY created_at ASC",
            (course_id,),
        )
        rows = cur.fetchall()

    return CourseSectionListResponse(
        sections=[CourseSectionResponse(id=row[0], name=row[1]) for row in rows]
    )


@router.post("/{course_id}/sections", response_model=CourseSectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    course_id: int,
    payload: CreateSectionRequest,
    current_user: dict = Depends(get_current_instructor),
):
    """Create a section for a course."""
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Section name is required")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO course_sections (course_id, name)
            VALUES (%s, %s)
            ON CONFLICT (course_id, name) DO NOTHING
            RETURNING id, name
            """,
            (course_id, name),
        )
        row = cur.fetchone()
        conn.commit()

        if not row:
            # Section already exists
            cur.execute(
                "SELECT id, name FROM course_sections WHERE course_id = %s AND name = %s",
                (course_id, name),
            )
            row = cur.fetchone()

    return CourseSectionResponse(id=row[0], name=row[1])


@router.delete("/{course_id}/sections/{section_id}", status_code=status.HTTP_200_OK)
async def delete_section(
    course_id: int,
    section_id: int,
    current_user: dict = Depends(get_current_instructor),
):
    """Delete a section if no students are assigned."""
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM course_sections WHERE id = %s AND course_id = %s",
            (section_id, course_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Section not found")

        cur.execute(
            "SELECT COUNT(*) FROM user_courses WHERE course_id = %s AND section_id = %s",
            (course_id, section_id),
        )
        if cur.fetchone()[0] > 0:
            raise HTTPException(status_code=400, detail="Cannot delete a section with students")

        cur.execute("DELETE FROM course_sections WHERE id = %s", (section_id,))
        conn.commit()

    return {"message": "Section deleted"}


@router.get("/{course_id}/sections/{section_id}/groups", response_model=SectionGroupListResponse)
async def list_groups(
    course_id: int,
    section_id: int,
    current_user: dict = Depends(get_current_instructor),
):
    """List groups for a section."""
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT g.id, g.name
            FROM section_groups g
            JOIN course_sections s ON s.id = g.section_id
            WHERE s.id = %s AND s.course_id = %s
            ORDER BY g.created_at ASC
            """,
            (section_id, course_id),
        )
        rows = cur.fetchall()

    return SectionGroupListResponse(groups=[SectionGroupResponse(id=row[0], name=row[1]) for row in rows])


@router.post("/{course_id}/sections/{section_id}/groups", response_model=SectionGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    course_id: int,
    section_id: int,
    payload: CreateGroupRequest,
    current_user: dict = Depends(get_current_instructor),
):
    """Create a group for a section."""
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM course_sections WHERE id = %s AND course_id = %s",
            (section_id, course_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Section not found")

        cur.execute(
            """
            INSERT INTO section_groups (section_id, name)
            VALUES (%s, %s)
            ON CONFLICT (section_id, name) DO NOTHING
            RETURNING id, name
            """,
            (section_id, name),
        )
        row = cur.fetchone()
        conn.commit()

        if not row:
            cur.execute(
                "SELECT id, name FROM section_groups WHERE section_id = %s AND name = %s",
                (section_id, name),
            )
            row = cur.fetchone()

    return SectionGroupResponse(id=row[0], name=row[1])


@router.delete("/{course_id}/sections/{section_id}/groups/{group_id}", status_code=status.HTTP_200_OK)
async def delete_group(
    course_id: int,
    section_id: int,
    group_id: int,
    current_user: dict = Depends(get_current_instructor),
):
    """Delete a group if no students are assigned."""
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT g.id
            FROM section_groups g
            JOIN course_sections s ON s.id = g.section_id
            WHERE g.id = %s AND s.id = %s AND s.course_id = %s
            """,
            (group_id, section_id, course_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Group not found")

        cur.execute(
            "SELECT COUNT(*) FROM user_courses WHERE course_id = %s AND group_id = %s",
            (course_id, group_id),
        )
        if cur.fetchone()[0] > 0:
            raise HTTPException(status_code=400, detail="Cannot delete a group with students")

        cur.execute("DELETE FROM section_groups WHERE id = %s", (group_id,))
        conn.commit()

    return {"message": "Group deleted"}


@router.post("/{course_id}/announcements", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    course_id: int,
    payload: CreateAnnouncementRequest,
    current_user: dict = Depends(get_current_instructor),
):
    """Create a course announcement."""
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Announcement message is required")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO course_announcements (course_id, message, created_by)
            VALUES (%s, %s, %s)
            RETURNING id, message, created_by, created_at
            """,
            (course_id, message, current_user["id"]),
        )
        row = cur.fetchone()
        conn.commit()

    return AnnouncementResponse(
        id=row[0],
        message=row[1],
        created_by=row[2],
        created_at=row[3].isoformat() if row[3] else None,
    )


@router.get("/{course_id}/announcements", response_model=AnnouncementListResponse)
async def list_announcements(
    course_id: int,
    current_user: dict = Depends(get_current_user),
):
    """List course announcements."""
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, message, created_by, created_at
            FROM course_announcements
            WHERE course_id = %s
            ORDER BY created_at DESC
            """,
            (course_id,),
        )
        rows = cur.fetchall()

    return AnnouncementListResponse(
        announcements=[
            AnnouncementResponse(
                id=row[0],
                message=row[1],
                created_by=row[2],
                created_at=row[3].isoformat() if row[3] else None,
            )
            for row in rows
        ]
    )


@router.get("/{course_id}/questions/export", status_code=status.HTTP_200_OK)
async def export_questions_csv(
    course_id: int,
    current_user: dict = Depends(get_current_instructor),
):
    """Export course questions as CSV."""
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(status_code=403, detail="You don't have access to this course")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT qh.id,
                   qh.question,
                   qh.answer,
                   qh.created_at,
                   u.email,
                   l.original_name
            FROM query_history qh
            LEFT JOIN users u ON u.id = qh.user_id
            LEFT JOIN lectures l ON l.id = qh.lecture_id
            WHERE (l.course_id = %s OR (qh.course_id = %s AND qh.lecture_id IS NULL))
            ORDER BY qh.created_at DESC
            """,
            (course_id, course_id),
        )
        rows = cur.fetchall()

    import csv
    from io import StringIO
    from fastapi.responses import Response

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "question", "answer", "created_at", "student_email", "lecture_name"])
    for row in rows:
        writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5]])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=course_{course_id}_questions.csv"},
    )

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