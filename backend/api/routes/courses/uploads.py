import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from ....core.config import UPLOAD_DIR
from ....db.postgres import (
    delete_upload_request,
    get_conn,
    get_upload_request,
    init_schema,
)
from ....ingestion.files import delete_stored_file
from ....ingestion.indexer import ingest_audio, ingest_pdf, ingest_slides
from ...middleware.auth import get_current_user
from ...models import UploadRequestListResponse, UploadRequestResponse, UploadResponse
from ..lectures import process_lecture_upload
from .shared import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    _build_upload_request_response,
    _file_type_from_extension,
    _is_ta_for_course,
    ensure_course_access,
    upload_request_to_response,
)

router = APIRouter()


@router.post("/{course_id}/lectures", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_lecture_to_course(
    course_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    ensure_course_access(course_id, current_user)
    if current_user["role"] == "student" and not _is_ta_for_course(current_user["id"], course_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students must request upload approval from instructor")
    return await process_lecture_upload(file, course_id=course_id, created_by=current_user["id"])


@router.post("/{course_id}/upload-requests", response_model=UploadRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_upload_request(
    course_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    ensure_course_access(course_id, current_user)
    if current_user["role"] == "student" and _is_ta_for_course(current_user["id"], course_id):
        await process_lecture_upload(file, course_id=course_id, created_by=current_user["id"])
        return _build_upload_request_response(
            course_id=course_id,
            student_id=current_user["id"],
            student_email=current_user["email"],
            original_name=file.filename or "upload",
            file_type="direct",
            status_value="approved",
        )
    if current_user["role"] != "student":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use direct upload for instructors")

    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type. Allowed: PDF, MP3, WAV, M4A, PPT, PPTX.")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB")

    file_type = _file_type_from_extension(file_ext)
    if not file_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")

    pending_dir = os.path.join(UPLOAD_DIR, "pending")
    os.makedirs(pending_dir, exist_ok=True)
    pending_path = os.path.join(pending_dir, f"{uuid4().hex}{file_ext}")
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
    return _build_upload_request_response(
        course_id=course_id,
        student_id=current_user["id"],
        student_email=current_user["email"],
        original_name=file.filename or "upload",
        file_type=file_type,
        status_value="pending",
        request_id=row[0],
        created_at=row[1],
    )


@router.get("/{course_id}/upload-requests", response_model=UploadRequestListResponse)
async def list_upload_requests(
    course_id: int,
    status_filter: str | None = Query(None, alias="status"),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != "instructor" and not _is_ta_for_course(current_user["id"], course_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Instructor or TA access required")
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        base_query = """
            SELECT r.id, r.course_id, r.student_id, u.email, r.original_name, r.file_type, r.status,
                   r.created_at, r.reviewed_by, r.reviewed_at
            FROM lecture_upload_requests r
            JOIN users u ON u.id = r.student_id
            WHERE r.course_id = %s
        """
        params = [course_id]
        if status_filter:
            base_query += " AND r.status = %s"
            params.append(status_filter)
        base_query += " ORDER BY r.created_at DESC"
        cur.execute(base_query, tuple(params))
        rows = cur.fetchall()
    return UploadRequestListResponse(requests=[upload_request_to_response(row) for row in rows])


@router.get("/{course_id}/upload-requests/mine", response_model=UploadRequestListResponse)
async def list_my_upload_requests(
    course_id: int,
    status: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    ensure_course_access(course_id, current_user)
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        base_query = """
            SELECT r.id, r.course_id, r.student_id, u.email, r.original_name, r.file_type, r.status,
                   r.created_at, r.reviewed_by, r.reviewed_at
            FROM lecture_upload_requests r
            JOIN users u ON u.id = r.student_id
            WHERE r.course_id = %s AND r.student_id = %s
        """
        params = [course_id, current_user["id"]]
        if status:
            base_query += " AND r.status = %s"
            params.append(status)
        base_query += " ORDER BY r.created_at DESC"
        cur.execute(base_query, tuple(params))
        rows = cur.fetchall()
    return UploadRequestListResponse(requests=[upload_request_to_response(row) for row in rows])


@router.post("/{course_id}/upload-requests/{request_id}/approve", response_model=UploadResponse)
async def approve_upload_request(course_id: int, request_id: int, current_user: dict = Depends(get_current_user)):
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
    delete_stored_file(file_path)
    return UploadResponse(lecture_id=lecture_id, message="Upload approved and processed successfully", status="completed")


@router.post("/{course_id}/upload-requests/{request_id}/reject", status_code=status.HTTP_200_OK)
async def reject_upload_request(course_id: int, request_id: int, current_user: dict = Depends(get_current_user)):
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
    delete_stored_file(row[0])
    return {"message": "Upload request rejected"}


@router.delete("/{course_id}/upload-requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload_request_route(course_id: int, request_id: int, current_user: dict = Depends(get_current_user)):
    row = get_upload_request(request_id)
    if not row or row[1] != course_id:
        raise HTTPException(status_code=404, detail="Upload request not found")
    student_id = row[2]
    file_path = row[4]
    request_status = row[6]
    is_owner = current_user["id"] == student_id
    is_staff = current_user["role"] == "instructor" or _is_ta_for_course(current_user["id"], course_id)
    if not is_owner and not is_staff:
        raise HTTPException(status_code=403, detail="You don't have access to this upload request")
    if is_owner and request_status not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=400, detail="This upload request cannot be removed")
    delete_upload_request(request_id)
    if request_status == "pending":
        delete_stored_file(file_path)
    return None
