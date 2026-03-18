#!/usr/bin/env python3
"""This file is a small local entrypoint for starting the backend API.
It runs Uvicorn with reload enabled so development changes are picked up automatically."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes
    )
