# src/api/routes/lectures.py
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from typing import List, Optional
import os
from pathlib import Path

from ...db import (
    get_lecture,
    list_lectures,
    delete_lecture,
    can_user_access_lecture,
    get_user_courses,
)
from ...rag_index import ingest_pdf, ingest_audio, ingest_slides
from ..models import (
    LectureResponse,
    LectureListResponse,
    UploadResponse,
    ErrorResponse,
    LectureAnalyticsResponse,
)
from ..middleware.auth import get_current_user, get_current_instructor
from ...analytics import get_lecture_analytics

router = APIRouter(prefix="/api/lectures", tags=["lectures"])

# Maximum file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024
PDF_EXTENSIONS = {".pdf"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
SLIDE_EXTENSIONS = {".pptx", ".ppt"}
ALLOWED_EXTENSIONS = PDF_EXTENSIONS | AUDIO_EXTENSIONS | SLIDE_EXTENSIONS

async def process_lecture_upload(file: UploadFile, course_id: Optional[int] = None, created_by: Optional[int] = None) -> UploadResponse:
    """
    Shared upload handler so both lecture and course routes can reuse validation and ingestion.
    """
    # Validate file type
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed: PDF, MP3, WAV, M4A.",
        )
    
    # Read file content
    contents = await file.read()
    
    # Validate file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB"
        )
    
    # Save file temporarily
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        tmp_file.write(contents)
        tmp_path = tmp_file.name
    
    try:
        if file_ext in PDF_EXTENSIONS:
            lecture_id = ingest_pdf(tmp_path, original_name=file.filename, course_id=course_id, created_by=created_by)
            file_type = "pdf"
        elif file_ext in AUDIO_EXTENSIONS:
            lecture_id = ingest_audio(tmp_path, original_name=file.filename, course_id=course_id, created_by=created_by)
            file_type = "audio"
        else:
            lecture_id = ingest_slides(tmp_path, original_name=file.filename, course_id=course_id, created_by=created_by)
            file_type = "slides"

        if lecture_id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process lecture file"
            )
        return UploadResponse(
            lecture_id=lecture_id,
            message=f"{file_type.upper()} uploaded and processed successfully",
            status="completed"
        )
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_lecture(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a PDF lecture file and process it (default course)."""
    return await process_lecture_upload(file, created_by=current_user["id"])

@router.get("", response_model=LectureListResponse)
async def list_all_lectures(
    course_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
):
    """List all lectures or filter by course (filtered by user access)."""
    lectures = list_lectures(course_id=course_id)
    
    # Filter lectures based on user role and enrollment
    if current_user["role"] == "student":
        # Students only see lectures in courses they're enrolled in (user_courses table)
        user_course_ids = get_user_courses(current_user["id"])
        lectures = [l for l in lectures if l[6] in user_course_ids]  # l[6] is course_id
    elif current_user["role"] == "instructor":
        # Instructors see lectures in courses they're assigned to (or all if no assignments exist)
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
                lectures = [l for l in lectures if l[6] in assigned_course_ids]
    
    lecture_responses = [
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
        for lect in lectures
    ]
    
    return LectureListResponse(
        lectures=lecture_responses,
        total=len(lecture_responses)
    )


@router.get("/{lecture_id}/analytics", response_model=LectureAnalyticsResponse)
async def get_lecture_analytics_route(
    lecture_id: int,
    current_user: dict = Depends(get_current_instructor),
):
    """Get analytics for a lecture (instructor only)."""
    lecture = get_lecture(lecture_id)
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with id {lecture_id} not found",
        )

    if not can_user_access_lecture(current_user["id"], lecture_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this lecture",
        )

    course_id = lecture[6]
    data = get_lecture_analytics(lecture_id=lecture_id, course_id=course_id)
    return LectureAnalyticsResponse(**data)

@router.get("/{lecture_id}", response_model=LectureResponse)
async def get_lecture_by_id(
    lecture_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Get lecture details by ID."""
    lecture = get_lecture(lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with id {lecture_id} not found"
        )
    
    # Check access
    if not can_user_access_lecture(current_user["id"], lecture_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this lecture",
        )
    
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

@router.get("/{lecture_id}/status", response_model=dict)
async def get_lecture_status(lecture_id: int):
    """Get processing status of a lecture."""
    lecture = get_lecture(lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with id {lecture_id} not found"
        )
    
    return {
        "lecture_id": lecture_id,
        "status": lecture[4],
        "page_count": lecture[3],
        "course_id": lecture[6],
        "file_type": lecture[7],
        "has_transcript": bool(lecture[8]),
    }

@router.delete("/{lecture_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lecture_by_id(
    lecture_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Delete a lecture and all its chunks."""
    lecture = get_lecture(lecture_id)
    
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with id {lecture_id} not found"
        )
    
    # Check access - only allow deletion if user is the creator or instructor
    if current_user["role"] != "instructor":
        # Students can only delete their own lectures
        if lecture[9] != current_user["id"]:  # created_by is at index 9
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete lectures you created",
            )
    
    # Delete lecture (cascade will delete chunks)
    delete_lecture(lecture_id)
    
    # Optionally delete the file (for now, keep it)
    # file_path = lecture[2]
    # if os.path.exists(file_path):
    #     os.unlink(file_path)
    
    return None

