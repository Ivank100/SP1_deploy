"""This file coordinates the ingestion pipeline after a lecture file is uploaded.
It decides how files are parsed, chunked, embedded, and saved to the database."""


import sys
from pathlib import Path
from typing import Any, Iterable

from .audio import chunk_transcript_segments, transcribe_audio
from .pdf import extract_text_with_pages, chunk_text_with_pages
from .slides import extract_text_with_slides, chunk_text_with_slides
from ..services.embeddings import embed_texts
from ..db.postgres import (
    insert_lecture,
    insert_chunks,
    save_lecture_transcript,
    update_lecture_status,
    clear_chunks_for_lecture,
    update_lecture_file,
    reset_lecture_materials,
)
from .files import save_uploaded_file

MAX_CHUNKS_FOR_V0 = 200  # allow more coverage for longer PDFs


def _embed_and_store_chunks(lecture_id: int, chunks_payload: Iterable[Any]):
    """Embed text chunks and persist them into the chunks table."""
    chunks_payload = list(chunks_payload)
    if not chunks_payload:
        raise ValueError("No chunks available for embedding")

    def _extract_text(entry: Any) -> str:
        if isinstance(entry, dict):
            return entry.get("text", "")
        if isinstance(entry, (list, tuple)) and entry:
            return str(entry[0])
        return str(entry)

    chunk_texts = [_extract_text(entry) for entry in chunks_payload]
    embeddings = embed_texts(chunk_texts)
    insert_chunks(lecture_id, chunks_payload, embeddings)

def ingest_pdf(path: str, original_name: str | None = None, course_id: int | None = None, created_by: int | None = None):
    """
    Ingest a PDF file: extract text, chunk, embed, and store in database.
    
    Args:
        path: Path to PDF file
        original_name: Optional original filename (for uploads)
    """
    print(f"[INFO] Reading PDF: {path}")

    # Extract text with page numbers
    text_pages = extract_text_with_pages(path)
    if not text_pages:
        print(f"[ERROR] No text found in PDF: {path}")
        print("This PDF may be scanned or image-only. Try another PDF with selectable text.")
        return None
    
    page_count = len(text_pages)
    print(f"[INFO] Extracted text from {page_count} pages")
    
    # Save file to uploads directory
    original_name = original_name or Path(path).name
    stored_path = save_uploaded_file(path, original_name)
    print(f"[INFO] Saved file to: {stored_path}")
    
    # Create lecture record
    lecture_id = insert_lecture(
        original_name=original_name,
        file_path=stored_path,
        page_count=page_count,
        status="processing",
        course_id=course_id,
        created_by=created_by,
    )
    print(f"[INFO] Created lecture record: id={lecture_id}")
    
    # Chunk text with page numbers
    chunks_with_pages = chunk_text_with_pages(text_pages)
    print(f"[INFO] Created {len(chunks_with_pages)} chunks before limiting")

    if len(chunks_with_pages) > MAX_CHUNKS_FOR_V0:
        print(f"[WARN] Too many chunks ({len(chunks_with_pages)}). Keeping only first {MAX_CHUNKS_FOR_V0}.")
        chunks_with_pages = chunks_with_pages[:MAX_CHUNKS_FOR_V0]

    if not chunks_with_pages:
        print(f"[ERROR] Could not create any chunks from PDF: {path}")
        update_lecture_status(lecture_id, "failed")
        return None
    
    print(f"[INFO] Embedding {len(chunks_with_pages)} chunks (pure Python, very light)...")
    _embed_and_store_chunks(lecture_id, chunks_with_pages)
    
    # Update status to completed
    update_lecture_status(lecture_id, "completed")
    
    print(f"[SUCCESS] Ingested {path} as lecture_id={lecture_id}, {len(chunks_with_pages)} chunks")
    return lecture_id


def replace_lecture_pdf(lecture_id: int, path: str, original_name: str | None = None):
    """
    Replace an existing lecture's PDF and reprocess chunks.
    """
    print(f"[INFO] Replacing PDF for lecture_id={lecture_id}: {path}")
    text_pages = extract_text_with_pages(path)
    if not text_pages:
        print(f"[ERROR] No text found in PDF: {path}")
        return None

    page_count = len(text_pages)
    original_name = original_name or Path(path).name
    stored_path = save_uploaded_file(path, original_name)
    print(f"[INFO] Saved replacement file to: {stored_path}")

    update_lecture_file(
        lecture_id=lecture_id,
        original_name=original_name,
        file_path=stored_path,
        page_count=page_count,
        file_type="pdf",
    )
    reset_lecture_materials(lecture_id)
    clear_chunks_for_lecture(lecture_id)

    chunks_with_pages = chunk_text_with_pages(text_pages)
    if len(chunks_with_pages) > MAX_CHUNKS_FOR_V0:
        print(f"[WARN] Too many chunks ({len(chunks_with_pages)}). Keeping only first {MAX_CHUNKS_FOR_V0}.")
        chunks_with_pages = chunks_with_pages[:MAX_CHUNKS_FOR_V0]

    if not chunks_with_pages:
        update_lecture_status(lecture_id, "failed")
        return None

    _embed_and_store_chunks(lecture_id, chunks_with_pages)
    update_lecture_status(lecture_id, "completed")
    print(f"[SUCCESS] Replaced lecture_id={lecture_id}, {len(chunks_with_pages)} chunks")
    return lecture_id

def ingest_audio(path: str, original_name: str | None = None, course_id: int | None = None, created_by: int | None = None):
    """
    Ingest an audio file by transcribing it with Whisper and chunking transcripts.
    """
    print(f"[INFO] Processing audio file: {path}")

    # Save audio file to uploads/audio
    original_name = original_name or Path(path).name
    stored_path = save_uploaded_file(path, original_name, subdir="audio")
    print(f"[INFO] Saved audio to: {stored_path}")

    lecture_id = insert_lecture(
        original_name=original_name,
        file_path=stored_path,
        page_count=0,
        status="processing",
        course_id=course_id,
        file_type="audio",
        created_by=created_by,
    )
    print(f"[INFO] Created audio lecture record: id={lecture_id}")

    try:
        update_lecture_status(lecture_id, "transcribing")
        transcript = transcribe_audio(stored_path)
        save_lecture_transcript(lecture_id, transcript)

        chunks_with_timestamps = chunk_transcript_segments(transcript)
        if len(chunks_with_timestamps) > MAX_CHUNKS_FOR_V0:
            print(
                f"[WARN] Too many transcript chunks ({len(chunks_with_timestamps)}). "
                f"Keeping only first {MAX_CHUNKS_FOR_V0}."
            )
            chunks_with_timestamps = chunks_with_timestamps[:MAX_CHUNKS_FOR_V0]

        print(f"[INFO] Embedding {len(chunks_with_timestamps)} transcript chunks...")
        _embed_and_store_chunks(lecture_id, chunks_with_timestamps)
        update_lecture_status(lecture_id, "completed")
    except Exception as exc:
        update_lecture_status(lecture_id, "failed")
        print(f"[ERROR] Failed to ingest audio lecture {lecture_id}: {exc}")
        raise

    print(f"[SUCCESS] Ingested audio as lecture_id={lecture_id}")
    return lecture_id


def ingest_slides(path: str, original_name: str | None = None, course_id: int | None = None, created_by: int | None = None):
    """
    Ingest a slide deck (PPT/PPTX): extract text per slide, chunk, embed, and store.
    """
    print(f"[INFO] Reading slides: {path}")

    slide_texts = extract_text_with_slides(path)
    if not slide_texts:
        print(f"[ERROR] No text found in slides: {path}")
        return None

    slide_count = len(slide_texts)
    print(f"[INFO] Extracted text from {slide_count} slides")

    # Save file to uploads/slides directory
    original_name = original_name or Path(path).name
    stored_path = save_uploaded_file(path, original_name, subdir="slides")
    print(f"[INFO] Saved slides to: {stored_path}")

    # Create lecture record
    lecture_id = insert_lecture(
        original_name=original_name,
        file_path=stored_path,
        page_count=slide_count,
        status="processing",
        course_id=course_id,
        file_type="slides",
        created_by=created_by,
    )
    print(f"[INFO] Created slides lecture record: id={lecture_id}")

    # Chunk slide text (treating slide numbers like page numbers)
    chunks_with_slides = chunk_text_with_slides(slide_texts)
    print(f"[INFO] Created {len(chunks_with_slides)} chunks before limiting")

    if len(chunks_with_slides) > MAX_CHUNKS_FOR_V0:
        print(
            f"[WARN] Too many chunks ({len(chunks_with_slides)}). "
            f"Keeping only first {MAX_CHUNKS_FOR_V0}."
        )
        chunks_with_slides = chunks_with_slides[:MAX_CHUNKS_FOR_V0]

    if not chunks_with_slides:
        print(f"[ERROR] Could not create any chunks from slides: {path}")
        update_lecture_status(lecture_id, "failed")
        return None

    print(f"[INFO] Embedding {len(chunks_with_slides)} chunks (pure Python, very light)...")
    _embed_and_store_chunks(lecture_id, chunks_with_slides)

    update_lecture_status(lecture_id, "completed")
    print(f"[SUCCESS] Ingested slides as lecture_id={lecture_id}, {len(chunks_with_slides)} chunks")
    return lecture_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m backend.ingestion.indexer path/to/file.pdf")
        sys.exit(1)
    ingest_pdf(sys.argv[1])
