from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional

from ...db import (
    get_lecture,
    can_user_access_lecture,
    create_flashcard_set,
    insert_flashcards,
    get_latest_flashcard_set,
    get_flashcard_set_by_id,
    list_flashcards_by_set,
    list_flashcards,
)
from ..middleware.auth import get_current_user
from ...study_materials import (
    get_materials,
    generate_summary,
    generate_key_points,
    generate_flashcards,
    LectureNotFoundError,
    LectureNotReadyError,
)
from ...flashcard_generator import generate_flashcards_v2
from ..models import (
    StudyMaterialsResponse,
    SummaryResponse,
    KeyPointsResponse,
    FlashcardListResponse,
    FlashcardGenerateRequest,
    FlashcardModel,
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
    """Legacy endpoint - redirects to new generate endpoint."""
    return await generate_flashcards_endpoint(lecture_id, current_user)


@router.post("/{lecture_id}/flashcards/generate", response_model=FlashcardListResponse)
async def generate_flashcards_endpoint(
    lecture_id: int,
    current_user: dict = Depends(get_current_user),
    request: FlashcardGenerateRequest = FlashcardGenerateRequest(),
):
    """Generate new flashcards for a lecture."""
    lecture = _ensure_lecture_exists(lecture_id)
    if not can_user_access_lecture(current_user["id"], lecture_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this lecture",
        )
    
    try:
        # Infer regenerate if lecture already has flashcard sets (defense in depth)
        regenerate = request.regenerate
        if not regenerate and get_latest_flashcard_set(lecture_id):
            regenerate = True

        # Generate flashcards using new pipeline
        flashcard_data = generate_flashcards_v2(
            lecture_id,
            user_id=current_user["id"],
            strategy=request.strategy,
            regenerate=regenerate,
            target_count=request.count,
        )
        
        # Create a new flashcard set
        set_id = create_flashcard_set(
            lecture_id,
            strategy=request.strategy,
            created_by_user_id=current_user["id"],
        )
        
        # Insert flashcards
        insert_flashcards(set_id, lecture_id, flashcard_data)
        
        # Fetch and return
        stored_rows = list_flashcards_by_set(set_id)
        cards = [
            FlashcardModel(
                id=row[0],
                question=row[1],
                answer=row[2],
                front=row[1],  # For backward compatibility
                back=row[2],   # For backward compatibility
                source_keypoint_id=row[3],
                quality_score=row[4],
            )
            for row in stored_rows
        ]
        
        return FlashcardListResponse(
            lecture_id=lecture_id,
            flashcards=cards,
            set_id=set_id,
            strategy=request.strategy,
        )
    
    except LectureNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{lecture_id}/flashcards/regenerate", response_model=FlashcardListResponse)
async def regenerate_flashcards(
    lecture_id: int,
    current_user: dict = Depends(get_current_user),
    request: Optional[FlashcardGenerateRequest] = None,
):
    """Regenerate flashcards for a lecture (creates a new set)."""
    if request is None:
        request = FlashcardGenerateRequest(regenerate=True)
    else:
        request.regenerate = True
    
    return await generate_flashcards_endpoint(lecture_id, current_user, request)


@router.get("/{lecture_id}/flashcards/latest", response_model=FlashcardListResponse)
async def get_latest_flashcards(
    lecture_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Get the latest flashcard set for a lecture."""
    lecture = _ensure_lecture_exists(lecture_id)
    if not can_user_access_lecture(current_user["id"], lecture_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this lecture",
        )
    
    set_info = get_latest_flashcard_set(lecture_id)
    if not set_info:
        # Return empty set
        return FlashcardListResponse(
            lecture_id=lecture_id,
            flashcards=[],
        )
    
    set_id, strategy, _ = set_info
    stored_rows = list_flashcards_by_set(set_id)
    cards = [
        FlashcardModel(
            id=row[0],
            question=row[1],
            answer=row[2],
            front=row[1],  # For backward compatibility
            back=row[2],   # For backward compatibility
            source_keypoint_id=row[3],
            quality_score=row[4],
        )
        for row in stored_rows
    ]
    
    return FlashcardListResponse(
        lecture_id=lecture_id,
        flashcards=cards,
        set_id=set_id,
        strategy=strategy,
    )


@router.get("/{lecture_id}/flashcards/sets/{set_id}", response_model=FlashcardListResponse)
async def get_flashcard_set(
    lecture_id: int,
    set_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Get a specific flashcard set by ID."""
    lecture = _ensure_lecture_exists(lecture_id)
    if not can_user_access_lecture(current_user["id"], lecture_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this lecture",
        )
    
    set_info = get_flashcard_set_by_id(set_id)
    if not set_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flashcard set {set_id} not found",
        )
    
    _, set_lecture_id, strategy, _ = set_info
    if set_lecture_id != lecture_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flashcard set {set_id} does not belong to lecture {lecture_id}",
        )
    
    stored_rows = list_flashcards_by_set(set_id)
    cards = [
        FlashcardModel(
            id=row[0],
            question=row[1],
            answer=row[2],
            front=row[1],  # For backward compatibility
            back=row[2],   # For backward compatibility
            source_keypoint_id=row[3],
            quality_score=row[4],
        )
        for row in stored_rows
    ]
    
    return FlashcardListResponse(
        lecture_id=lecture_id,
        flashcards=cards,
        set_id=set_id,
        strategy=strategy,
    )

