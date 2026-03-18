"""This file marks the lectures folder as a Python package.
It also exposes shared imports when this package is loaded elsewhere."""


from fastapi import APIRouter

from . import files, read, resources, write
from .shared import process_lecture_upload

router = APIRouter(prefix="/api/lectures", tags=["lectures"])
router.include_router(read.router)
router.include_router(write.router)
router.include_router(resources.router)
router.include_router(files.router)
