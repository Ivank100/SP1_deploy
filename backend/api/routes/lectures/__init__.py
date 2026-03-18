from fastapi import APIRouter

from . import files, read, resources, write
from .shared import process_lecture_upload

router = APIRouter(prefix="/api/lectures", tags=["lectures"])
router.include_router(read.router)
router.include_router(write.router)
router.include_router(resources.router)
router.include_router(files.router)
