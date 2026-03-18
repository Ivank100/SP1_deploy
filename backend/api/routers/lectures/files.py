import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ...dependencies.auth import get_current_user
from ...schemas import UploadResponse
from ...services.uploads import DOCUMENT_EXTENSIONS, MAX_FILE_SIZE
from .shared import ensure_lecture_access, get_lecture_or_404, process_lecture_upload, replace_lecture_pdf

router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_lecture(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    return await process_lecture_upload(file, created_by=current_user["id"])


@router.post("/{lecture_id}/replace", response_model=UploadResponse)
async def replace_lecture_file(
    lecture_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    lecture = ensure_lecture_access(lecture_id, current_user)
    if current_user["role"] != "instructor" and lecture[9] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only replace lectures you created")
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in DOCUMENT_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF/DOCX replacement is supported")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB")

    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        tmp_file.write(contents)
        tmp_path = tmp_file.name
    try:
        replaced = replace_lecture_pdf(lecture_id, tmp_path, original_name=file.filename)
        if replaced is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to replace lecture")
        return UploadResponse(lecture_id=lecture_id, message="Lecture replaced and reprocessed successfully", status="completed")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
