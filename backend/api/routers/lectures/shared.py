"""This file stores helper logic shared by lecture route modules.
It keeps repeated permission checks, mappings, and response helpers together."""


import os
from pathlib import Path
import tempfile
from typing import Optional

from fastapi import HTTPException, status

from ....db.postgres import (
    add_lecture_resource,
    delete_lecture,
    delete_lecture_resource,
    get_instructor_visible_course_ids,
    get_lecture,
    get_user_courses,
    list_lecture_resources,
    list_lectures,
    update_lecture_name,
    update_lecture_status,
)
from ....ingestion.files import delete_stored_file
from ....ingestion.indexer import ingest_audio, ingest_pdf, ingest_slides, replace_lecture_pdf
from ....services.analytics import get_lecture_analytics
from ...schemas import UploadResponse
from ...services.permissions import ensure_lecture_access, get_lecture_or_404
from ...services.responses import lecture_to_response
from ...services.uploads import AUDIO_EXTENSIONS, DOCUMENT_EXTENSIONS, MAX_FILE_SIZE, SLIDE_EXTENSIONS

ALLOWED_EXTENSIONS = DOCUMENT_EXTENSIONS | AUDIO_EXTENSIONS | SLIDE_EXTENSIONS


async def process_lecture_upload(file, course_id: Optional[int] = None, created_by: Optional[int] = None) -> UploadResponse:
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type. Allowed: PDF, DOCX, MP3, WAV, M4A, PPT, PPTX.")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB")
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        tmp_file.write(contents)
        tmp_path = tmp_file.name
    try:
        if file_ext in DOCUMENT_EXTENSIONS:
            lecture_id = ingest_pdf(tmp_path, original_name=file.filename, course_id=course_id, created_by=created_by)
            file_type = "pdf"
        elif file_ext in AUDIO_EXTENSIONS:
            lecture_id = ingest_audio(tmp_path, original_name=file.filename, course_id=course_id, created_by=created_by)
            file_type = "audio"
        else:
            lecture_id = ingest_slides(tmp_path, original_name=file.filename, course_id=course_id, created_by=created_by)
            file_type = "slides"
        if lecture_id is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process lecture file")
        return UploadResponse(lecture_id=lecture_id, message=f"{file_type.upper()} uploaded and processed successfully", status="completed")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
