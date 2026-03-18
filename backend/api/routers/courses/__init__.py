"""This file marks the courses folder as a Python package.
It also exposes shared imports when this package is loaded elsewhere."""


from fastapi import APIRouter

from . import announcements, analytics, read, students, uploads, write

router = APIRouter(prefix="/api/courses", tags=["courses"])
router.include_router(read.router)
router.include_router(write.router)
router.include_router(uploads.router)
router.include_router(students.router)
router.include_router(announcements.router)
router.include_router(analytics.router)
