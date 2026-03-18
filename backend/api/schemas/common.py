"""This file defines Pydantic schemas for common API payloads.
These models validate request bodies and keep response shapes consistent."""


from typing import Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

