"""Utilities for parsing slide decks (PPT/PPTX) into text with slide numbers using Docling."""
from collections import defaultdict
from typing import List, Tuple

from .pdf_utils import _get_converter, chunk_text_with_pages


def extract_text_with_slides(path: str) -> List[Tuple[str, int]]:
    """
    Extract text content from each slide in a PowerPoint file using Docling.

    Docling maps each slide to a page_no in element provenance, so slide numbers
    are recovered the same way as PDF page numbers.

    Returns a list of (text, slide_number) tuples.
    """
    result = _get_converter().convert(path)
    doc = result.document

    slides_text: dict[int, list[str]] = defaultdict(list)

    for item in doc.texts:
        if item.prov:
            slide_no = item.prov[0].page_no
            text = item.text.strip()
            if text:
                slides_text[slide_no].append(text)

    for table in doc.tables:
        if table.prov:
            slide_no = table.prov[0].page_no
            try:
                table_md = table.export_to_markdown()
                if table_md.strip():
                    slides_text[slide_no].append(table_md)
            except Exception:
                pass

    return [
        ("\n".join(texts), slide_no)
        for slide_no, texts in sorted(slides_text.items())
        if texts
    ]


def chunk_text_with_slides(
    slide_texts: List[Tuple[str, int]],
    max_chars: int = 1500,
    overlap: int = 200,
) -> List[Tuple[str, int]]:
    """
    Chunk slide text while preserving slide numbers.

    Uses the same chunking strategy as PDFs, treating slide numbers
    analogously to page numbers.
    """
    return chunk_text_with_pages(slide_texts, max_chars=max_chars, overlap=overlap)
