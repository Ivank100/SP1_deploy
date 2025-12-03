# src/pdf_utils.py
import fitz  # PyMuPDF
from typing import List, Tuple

def extract_text_from_pdf(path: str) -> str:
    """Legacy function: extract all text without page tracking."""
    doc = fitz.open(path)
    texts = []
    for page in doc:
        texts.append(page.get_text())
    doc.close()
    return "\n".join(texts)

def extract_text_with_pages(path: str) -> List[Tuple[str, int]]:
    """
    Extract text from PDF with page number tracking.
    
    Returns:
        List of (text, page_number) tuples
    """
    doc = fitz.open(path)
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():  # Only include non-empty pages
            pages.append((text, page_num))
    doc.close()
    return pages

def chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> List[str]:
    """Legacy function: chunk text without page tracking."""
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

def chunk_text_with_pages(text_pages: List[Tuple[str, int]], 
                          max_chars: int = 1500, 
                          overlap: int = 200) -> List[Tuple[str, int]]:
    """
    Chunk text from multiple pages, preserving page numbers.
    
    Args:
        text_pages: List of (text, page_number) tuples
        max_chars: Maximum characters per chunk
        overlap: Overlap between chunks in characters
        
    Returns:
        List of (chunk_text, page_number) tuples
        If a chunk spans multiple pages, uses the starting page number
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if overlap >= max_chars:
        raise ValueError("overlap must be < max_chars")
    
    chunks = []
    
    # Combine all pages into one text with page markers
    combined_text = ""
    page_map = []  # Maps character position to page number
    
    for text, page_num in text_pages:
        start_pos = len(combined_text)
        combined_text += text + "\n"
        # Map all characters in this page to this page number
        for i in range(len(text) + 1):  # +1 for the newline
            page_map.append(page_num)
    
    # Now chunk the combined text
    start = 0
    while start < len(combined_text):
        end = min(len(combined_text), start + max_chars)
        chunk_text = combined_text[start:end]
        
        # Get the page number for the start of this chunk
        chunk_page = page_map[start] if start < len(page_map) else page_map[-1] if page_map else 1
        
        chunks.append((chunk_text.strip(), chunk_page))
        
        # If we've reached the end, stop
        if end >= len(combined_text):
            break
        
        # Move start forward with overlap
        start = end - overlap
    
    return chunks