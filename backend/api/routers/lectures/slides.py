from collections import defaultdict

from fastapi import APIRouter, HTTPException, status

from ....db.postgres import get_chunks_for_lecture, get_lecture
from ...schemas import ErrorResponse, SlideListResponse, SlideResponse

router = APIRouter(prefix="/api/lectures", tags=["slides"])


@router.get(
    "/{lecture_id}/slides",
    response_model=SlideListResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_slides(lecture_id: int):
    """
    Return slide-level text for a slides lecture by aggregating chunks per slide number.
    """
    lecture = get_lecture(lecture_id)
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with id {lecture_id} not found",
        )

    if lecture[7] != "slides":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slides endpoint is only available for slide lectures",
        )

    chunks = get_chunks_for_lecture(lecture_id)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No slide content found for this lecture",
        )

    by_slide = defaultdict(list)
    for text, page_number, ts_start, ts_end in chunks:
        slide_no = page_number or 1
        by_slide[slide_no].append(text.strip())

    slides = [
        SlideResponse(slide_number=slide_no, text="\n\n".join(parts))
        for slide_no, parts in sorted(by_slide.items(), key=lambda kv: kv[0])
    ]

    return SlideListResponse(lecture_id=lecture_id, slides=slides, total=len(slides))

