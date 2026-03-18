from collections import defaultdict
import os
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from ....core.config import UPLOAD_DIR
from ....db.postgres import (
    can_user_access_course,
    create_course,
    delete_course_as_instructor,
    delete_upload_request,
    get_conn,
    get_course,
    get_instructor_visible_course_ids,
    get_upload_request,
    get_user_courses,
    init_schema,
    list_courses,
    list_lectures,
    list_upload_request_file_paths,
)
from ....ingestion.files import delete_stored_file
from ...common import lecture_to_response, upload_request_to_response
from ...models import CourseResponse, UploadRequestResponse
from ...upload_config import AUDIO_EXTENSIONS, MAX_FILE_SIZE, PDF_EXTENSIONS, SLIDE_EXTENSIONS

ALLOWED_EXTENSIONS = PDF_EXTENSIONS | AUDIO_EXTENSIONS | SLIDE_EXTENSIONS


def _file_type_from_extension(file_ext: str):
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


def _build_upload_request_response(
    course_id: int,
    student_id: int,
    student_email: str,
    original_name: str,
    file_type: str,
    status_value: str,
    request_id: int = 0,
    created_at=None,
) -> UploadRequestResponse:
    return UploadRequestResponse(
        id=request_id,
        course_id=course_id,
        student_id=student_id,
        student_email=student_email,
        original_name=original_name,
        file_type=file_type,
        status=status_value,
        created_at=created_at.isoformat() if created_at else None,
    )


def get_course_or_404(course_id: int):
    course = get_course(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )
    return course


def ensure_course_access(course_id: int, current_user: dict):
    course = get_course_or_404(course_id)
    if not can_user_access_course(current_user["id"], course_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this course",
        )
    return course


def build_course_list_response(current_user: dict):
    courses = list_courses()
    lectures = list_lectures()

    if current_user["role"] == "student":
        user_course_ids = get_user_courses(current_user["id"])
        courses = [c for c in courses if c[0] in user_course_ids]
        lectures = [l for l in lectures if l[6] in user_course_ids]
    elif current_user["role"] == "instructor":
        visible_course_ids = get_instructor_visible_course_ids(current_user["id"])
        if visible_course_ids is not None:
            courses = [c for c in courses if c[0] in visible_course_ids]
            lectures = [l for l in lectures if l[6] in visible_course_ids]

    lectures_by_course = defaultdict(list)
    for lect in lectures:
        lectures_by_course[lect[6]].append(lect)

    course_responses = []
    for course in courses:
        course_id = course[0]
        course_lectures = [lecture_to_response(lect) for lect in lectures_by_course.get(course_id, [])]
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
    return course_responses


def delete_course_and_files(course_id: int, instructor_id: int) -> None:
    lectures = list_lectures(course_id=course_id)
    pending_file_paths = list_upload_request_file_paths(course_id)
    delete_course_as_instructor(course_id, instructor_id)
    for lect in lectures:
        delete_stored_file(lect[2])
    for pending_path in pending_file_paths:
        delete_stored_file(pending_path)
