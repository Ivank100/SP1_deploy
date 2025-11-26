import uuid
import sys
from .pdf_utils import extract_text_from_pdf, chunk_text
from .embedding_model import embed_texts
from .db import insert_chunks

MAX_CHUNKS_FOR_V0 = 80  # safe for your size

def ingest_pdf(path: str):
    print(f"[INFO] Reading PDF: {path}")
    raw_text = extract_text_from_pdf(path)
    print(f"[INFO] Extracted {len(raw_text)} characters of text")

    if not raw_text.strip():
        print(f"[ERROR] No text found in PDF: {path}")
        print("This PDF may be scanned or image-only. Try another PDF with selectable text.")
        return

    chunks = chunk_text(raw_text)
    print(f"[INFO] Created {len(chunks)} chunks before limiting")

    if len(chunks) > MAX_CHUNKS_FOR_V0:
        print(f"[WARN] Too many chunks ({len(chunks)}). Keeping only first {MAX_CHUNKS_FOR_V0}.")
        chunks = chunks[:MAX_CHUNKS_FOR_V0]

    if not chunks:
        print(f"[ERROR] Could not create any chunks from PDF: {path}")
        return

    print(f"[INFO] Embedding {len(chunks)} chunks (pure Python, very light)...")
    embeddings = embed_texts(chunks)

    doc_id = str(uuid.uuid4())
    insert_chunks(doc_id, chunks, embeddings)
    print(f"[SUCCESS] Ingested {path} as doc_id={doc_id}, {len(chunks)} chunks")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.rag_index path/to/file.pdf")
        sys.exit(1)
    ingest_pdf(sys.argv[1])
