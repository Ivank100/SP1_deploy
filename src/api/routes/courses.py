from collections import defaultdict
from fastapi import APIRouter, HTTPException, UploadFile, File, status, Depends

from ...db import (
    list_courses,
    list_lectures,
    get_course,
    create_course,
    can_user_access_course,
    add_user_to_course,
)
from ..middleware.auth import get_current_user
from ...rag_query import answer_question
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
        from ...db import get_conn, init_schema
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
                courses = [c for c in courses if c[0] in assigned_course_ids]
                lectures = [l for l in lectures if l[6] in assigned_course_ids]

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
                lecture_count=len(course_lectures),
                lectures=course_lectures,
            )
        )

    return CourseListResponse(courses=course_responses, total=len(course_responses))


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_new_course(
    request: CreateCourseRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new course."""
    name = request.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course name cannot be empty",
        )

    course_id = create_course(name=name, description=request.description, created_by=current_user["id"])
    
    # Automatically enroll the creator in the course
    add_user_to_course(current_user["id"], course_id)
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
    """Ask a question across all lectures in a course."""
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

