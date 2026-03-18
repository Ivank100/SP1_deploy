# src/api/routes/queries.py
from fastapi import APIRouter, HTTPException, status, Depends

from ....db.postgres import get_conn
from ....services.rag import answer_question
from ...dependencies.auth import get_current_user
from ...schemas import (
    ErrorResponse,
    QueryHistoryItem,
    QueryHistoryResponse,
    QueryRequest,
    QueryResponse,
)
from ...services.permissions import ensure_lecture_access
from ...services.responses import query_history_item_from_row

router = APIRouter(prefix="/api/lectures", tags=["queries"])

@router.post("/{lecture_id}/query", response_model=QueryResponse)
async def query_lecture(
    lecture_id: int,
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Ask a question about a specific lecture.
    
    Returns answer with citations.
    """
    # Verify lecture exists
    lecture = ensure_lecture_access(lecture_id, current_user)
    
    # Check if lecture is ready
    if lecture[4] != "completed":  # status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lecture is not ready. Current status: {lecture[4]}"
        )
    
    # Get answer with citation
    course_id = lecture[6]
    answer, citation, sources = answer_question(
        question=request.question,
        lecture_id=lecture_id,
        course_id=course_id,
        top_k=request.top_k,
        user_id=current_user["id"],
        query_mode=request.query_mode,
    )
    
    return QueryResponse(
        answer=answer,
        citation=citation,
        lecture_id=lecture_id,
        course_id=course_id,
        sources=sources,
    )

@router.get("/{lecture_id}/history", response_model=QueryHistoryResponse)
async def get_query_history_for_lecture(
    lecture_id: int,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """
    Get query history for a specific lecture.
    """
    # Verify lecture exists
    ensure_lecture_access(lecture_id, current_user)
    
    # Query directly from DB with lecture_id filter
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT qh.id, qh.question, qh.answer, qh.created_at, u.email, qh.page_number
            FROM query_history qh
            LEFT JOIN users u ON u.id = qh.user_id
            WHERE qh.lecture_id = %s
            ORDER BY qh.created_at DESC
            LIMIT %s
            """,
            (lecture_id, limit),
        )
        history_items = cur.fetchall()
    
    query_items = [query_history_item_from_row(item) for item in history_items]
    
    return QueryHistoryResponse(
        queries=query_items,
        total=len(query_items)
    )
