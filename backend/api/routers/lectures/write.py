from fastapi import APIRouter, Depends, HTTPException, status

from ...dependencies.auth import get_current_user
from ...schemas import LectureRenameRequest, LectureResponse
from .shared import delete_lecture, delete_stored_file, ensure_lecture_access, get_lecture_or_404, lecture_to_response, update_lecture_name, update_lecture_status

router = APIRouter()


@router.delete("/{lecture_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lecture_by_id(lecture_id: int, current_user: dict = Depends(get_current_user)):
    lecture = get_lecture_or_404(lecture_id)
    if current_user["role"] != "instructor" and lecture[9] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete lectures you created")
    file_path = lecture[2]
    delete_lecture(lecture_id)
    delete_stored_file(file_path)
    return None


@router.patch("/{lecture_id}/rename", response_model=LectureResponse)
async def rename_lecture(lecture_id: int, payload: LectureRenameRequest, current_user: dict = Depends(get_current_user)):
    lecture = ensure_lecture_access(lecture_id, current_user)
    if current_user["role"] != "instructor" and lecture[9] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only rename lectures you created")
    update_lecture_name(lecture_id, payload.name)
    return lecture_to_response(get_lecture_or_404(lecture_id))


@router.patch("/{lecture_id}/archive", response_model=dict)
async def archive_lecture(lecture_id: int, current_user: dict = Depends(get_current_user)):
    get_lecture_or_404(lecture_id)
    if current_user["role"] != "instructor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only instructors can archive lectures")
    update_lecture_status(lecture_id, "archived")
    return {"message": "Lecture archived"}
