"""This file builds the main FastAPI application object.
It wires middleware, routers, static uploads, and health endpoints into one app."""


from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..core.config import UPLOAD_DIR
from .routers import auth, courses, instructor, lectures
from .routers.lectures import audio, queries, slides, study_materials

app = FastAPI(
    title="LectureSense API",
    description="RAG-based lecture Q&A system",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(lectures.router)
app.include_router(queries.router)
app.include_router(courses.router)
app.include_router(study_materials.router)
app.include_router(audio.router)
app.include_router(instructor.router)
app.include_router(slides.router)

uploads_path = Path(UPLOAD_DIR).resolve()
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")


@app.get("/")
async def root():
    return {
        "message": "LectureSense API",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

