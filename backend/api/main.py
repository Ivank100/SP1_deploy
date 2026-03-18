"""This file is the simplest executable entrypoint for the FastAPI app.
It imports the shared app instance and starts Uvicorn when run directly."""


from .app import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
