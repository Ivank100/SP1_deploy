#!/usr/bin/env python3
"""
Run the LectureSense API server.

Usage:
    python run_api.py

Or with uvicorn directly:
    uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes
    )
