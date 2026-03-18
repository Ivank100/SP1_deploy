"""This file contains API-facing service helpers for uploads flows.
It keeps route handlers smaller by moving shared non-router logic out of endpoint functions."""


MAX_FILE_SIZE = 50 * 1024 * 1024
DOCUMENT_EXTENSIONS = {".pdf", ".docx"}
PDF_EXTENSIONS = {".pdf"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
SLIDE_EXTENSIONS = {".pptx", ".ppt"}

