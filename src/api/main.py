# src/api/main.py
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..core.config import UPLOAD_DIR
from .routes import audio, auth, courses, instructor, lectures, queries, slides, study_materials

app = FastAPI(
    title="LectureSense API",
    description="RAG-based lecture Q&A system",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],  # Explicitly allow Authorization header
)

# Include routers
app.include_router(auth.router)
app.include_router(lectures.router)
app.include_router(queries.router)
app.include_router(courses.router)
app.include_router(study_materials.router)
app.include_router(audio.router)
app.include_router(instructor.router)
app.include_router(slides.router)

# Serve uploaded files (PDF/audio) for playback/downloading
uploads_path = Path(UPLOAD_DIR).resolve()
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LectureSense API",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

