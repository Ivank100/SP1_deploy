from fastapi import APIRouter, HTTPException, status, Depends

from ...db import get_lecture, can_user_access_lecture
from ..middleware.auth import get_current_user
from ...study_materials import (
    get_materials,
    generate_summary,
    generate_key_points,
    generate_flashcards,
    LectureNotFoundError,
    LectureNotReadyError,
)
from ..models import (
    StudyMaterialsResponse,
    SummaryResponse,
    KeyPointsResponse,
    FlashcardListResponse,
)

router = APIRouter(prefix="/api/lectures", tags=["study-materials"])


def _ensure_lecture_exists(lecture_id: int):
    lecture = get_lecture(lecture_id)
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with id {lecture_id} not found",
        )
    return lecture


@router.get("/{lecture_id}/study-materials", response_model=StudyMaterialsResponse)
async def get_study_materials(
    lecture_id: int,
    current_user: dict = Depends(get_current_user),
):
    lecture = _ensure_lecture_exists(lecture_id)
    if not can_user_access_lecture(current_user["id"], lecture_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this lecture",
        )
    materials = get_materials(lecture_id)
    return StudyMaterialsResponse(
        lecture_id=lecture_id,
        summary=materials["summary"],
        key_points=materials["key_points"],
        flashcards=materials["flashcards"],
    )


@router.post("/{lecture_id}/summarize", response_model=SummaryResponse)
async def summarize_lecture(
    lecture_id: int,
    current_user: dict = Depends(get_current_user),
):
    lecture = _ensure_lecture_exists(lecture_id)
    if not can_user_access_lecture(current_user["id"], lecture_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this lecture",
        )
    try:
        summary = generate_summary(lecture_id)
    except LectureNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (ValueError, LectureNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SummaryResponse(lecture_id=lecture_id, summary=summary, cached=False)


@router.post("/{lecture_id}/key-points", response_model=KeyPointsResponse)
async def key_points(
    lecture_id: int,
    current_user: dict = Depends(get_current_user),
):
    lecture = _ensure_lecture_exists(lecture_id)
    if not can_user_access_lecture(current_user["id"], lecture_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this lecture",
        )
    try:
        points = generate_key_points(lecture_id)
    except LectureNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (ValueError, LectureNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return KeyPointsResponse(lecture_id=lecture_id, key_points=points, cached=False)


@router.post("/{lecture_id}/flashcards", response_model=FlashcardListResponse)
async def flashcards(
    lecture_id: int,
    current_user: dict = Depends(get_current_user),
):
    lecture = _ensure_lecture_exists(lecture_id)
    if not can_user_access_lecture(current_user["id"], lecture_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this lecture",
        )
    try:
        cards = generate_flashcards(lecture_id)
    except LectureNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return FlashcardListResponse(lecture_id=lecture_id, flashcards=cards)

