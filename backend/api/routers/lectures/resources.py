from fastapi import APIRouter, Depends, HTTPException, status

from ...dependencies.auth import get_current_user
from ...schemas import LectureResource, LectureResourceCreateRequest, LectureResourceListResponse
from .shared import add_lecture_resource, delete_lecture_resource, ensure_lecture_access, get_lecture_or_404, list_lecture_resources

router = APIRouter()


@router.get("/{lecture_id}/resources", response_model=LectureResourceListResponse)
async def get_lecture_resources(lecture_id: int, current_user: dict = Depends(get_current_user)):
    ensure_lecture_access(lecture_id, current_user)
    rows = list_lecture_resources(lecture_id)
    resources = [LectureResource(id=r[0], lecture_id=r[1], title=r[2], url=r[3], created_at=r[4]) for r in rows]
    return LectureResourceListResponse(resources=resources)


@router.post("/{lecture_id}/resources", response_model=LectureResource)
async def add_resource_to_lecture(lecture_id: int, payload: LectureResourceCreateRequest, current_user: dict = Depends(get_current_user)):
    get_lecture_or_404(lecture_id)
    if current_user["role"] != "instructor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only instructors can add resources")
    resource = add_lecture_resource(lecture_id, payload.title, payload.url)
    return LectureResource(id=resource[0], lecture_id=resource[1], title=resource[2], url=resource[3], created_at=resource[4])


@router.delete("/{lecture_id}/resources/{resource_id}", response_model=dict)
async def remove_resource_from_lecture(lecture_id: int, resource_id: int, current_user: dict = Depends(get_current_user)):
    get_lecture_or_404(lecture_id)
    if current_user["role"] != "instructor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only instructors can delete resources")
    delete_lecture_resource(resource_id)
    return {"message": "Resource deleted"}
