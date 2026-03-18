"""This file defines course announcement endpoints.
It handles creating, listing, and managing announcement records tied to a course."""


from fastapi import APIRouter, Depends, HTTPException, status

from ....db.postgres import get_conn
from ...dependencies.auth import get_current_instructor, get_current_user
from ...schemas import AnnouncementListResponse, AnnouncementResponse, CreateAnnouncementRequest
from .shared import ensure_course_access

router = APIRouter()


@router.post("/{course_id}/announcements", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    course_id: int,
    payload: CreateAnnouncementRequest,
    current_user: dict = Depends(get_current_instructor),
):
    ensure_course_access(course_id, current_user)
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Announcement message is required")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO course_announcements (course_id, message, created_by)
            VALUES (%s, %s, %s)
            RETURNING id, message, created_by, created_at
            """,
            (course_id, message, current_user["id"]),
        )
        row = cur.fetchone()
        conn.commit()
    return AnnouncementResponse(id=row[0], message=row[1], created_by=row[2], created_at=row[3].isoformat() if row[3] else None)


@router.get("/{course_id}/announcements", response_model=AnnouncementListResponse)
async def list_announcements(course_id: int, current_user: dict = Depends(get_current_user)):
    ensure_course_access(course_id, current_user)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, message, created_by, created_at
            FROM course_announcements
            WHERE course_id = %s
            ORDER BY created_at DESC
            """,
            (course_id,),
        )
        rows = cur.fetchall()
    return AnnouncementListResponse(
        announcements=[
            AnnouncementResponse(
                id=row[0],
                message=row[1],
                created_by=row[2],
                created_at=row[3].isoformat() if row[3] else None,
            )
            for row in rows
        ]
    )
