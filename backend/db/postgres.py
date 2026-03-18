"""Compatibility export layer for the Postgres DB modules."""

from .chunks import (
    clear_chunks_for_lecture,
    get_chunks_for_page,
    get_chunks_for_lecture,
    insert_chunks,
    list_chunk_records,
    search_by_reference_patterns,
    search_by_keywords,
    search_similar,
    update_chunk_embeddings,
)
from .connection import (
    DEFAULT_COURSE_DESCRIPTION,
    DEFAULT_COURSE_NAME,
    FILE_TYPES,
    generate_join_code,
    get_conn,
)
from .courses import (
    assign_instructor_to_course,
    can_user_access_course,
    create_course,
    delete_course_as_instructor,
    enroll_student_by_code,
    get_course,
    get_instructor_assigned_course_ids,
    get_instructor_visible_course_ids,
    is_instructor_for_course,
    list_courses,
)
from .flashcards import (
    create_flashcard_set,
    get_flashcard_set_by_id,
    get_latest_flashcard_set,
    get_previous_flashcard_questions,
    insert_flashcards,
    list_flashcards_by_set,
)
from .lectures import (
    add_lecture_resource,
    can_user_access_lecture,
    delete_lecture,
    delete_lecture_resource,
    get_lecture,
    get_lecture_study_materials,
    get_lecture_transcript,
    insert_lecture,
    list_lecture_resources,
    list_lectures,
    reset_lecture_materials,
    save_lecture_key_points,
    save_lecture_summary,
    save_lecture_transcript,
    update_lecture_file,
    update_lecture_name,
    update_lecture_status,
)
from .queries import insert_query
from .schema import _get_or_create_default_course, ensure_default_course, init_schema
from .upload_requests import (
    delete_upload_request,
    get_upload_request,
    list_upload_request_file_paths,
)
from .users import (
    add_user_to_course,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_courses,
    get_user_courses_with_details,
)
