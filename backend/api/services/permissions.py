"""This file contains API-facing service helpers for permissions flows.
It keeps route handlers smaller by moving shared non-router logic out of endpoint functions."""


from fastapi import HTTPException, status

from ...db.postgres import can_user_access_lecture, get_lecture


def get_lecture_or_404(lecture_id: int):
    lecture = get_lecture(lecture_id)
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lecture with id {lecture_id} not found",
        )
    return lecture


def ensure_lecture_access(lecture_id: int, current_user: dict):
    lecture = get_lecture_or_404(lecture_id)
    if not can_user_access_lecture(current_user["id"], lecture_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this lecture",
        )
    return lecture

