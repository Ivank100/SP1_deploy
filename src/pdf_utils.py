# src/pdf_utils.py
import fitz  # PyMuPDF
from typing import List

def extract_text_from_pdf(path: str) -> str:
    doc = fitz.open(path)
    texts = []
    for page in doc:
        texts.append(page.get_text())
    doc.close()
    return "\n".join(texts)

def chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> List[str]:
    chunks = []
    start = 0

    # guard: avoid bad parameters
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if overlap >= max_chars:
        raise ValueError("overlap must be < max_chars")

    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end])

        # if we've reached the end, stop
        if end >= len(text):
            break

        # move start forward with overlap
        start = end - overlap

    return chunks