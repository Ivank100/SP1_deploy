# src/pdf_utils.py
from collections import defaultdict
from typing import List, Tuple

from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions

_converter_no_ocr: DocumentConverter | None = None
_converter_ocr: DocumentConverter | None = None


def _get_converter(ocr: bool = False) -> DocumentConverter:
    global _converter_no_ocr, _converter_ocr
    if not ocr:
        if _converter_no_ocr is None:
            _converter_no_ocr = DocumentConverter(
                pipeline_options=PdfPipelineOptions(do_ocr=False)
            )
        return _converter_no_ocr
    else:
        if _converter_ocr is None:
            _converter_ocr = DocumentConverter()
        return _converter_ocr


def extract_text_from_pdf(path: str) -> str:
    """Legacy function: extract all text without page tracking."""
    result = _get_converter(ocr=False).convert(path)
    return result.document.export_to_text()


def _extract_pages_from_doc(doc) -> dict:
    pages_text: dict[int, list[str]] = defaultdict(list)
    for item in doc.texts:
        if item.prov:
            page_no = item.prov[0].page_no
            text = item.text.strip()
            if text:
                pages_text[page_no].append(text)
    for table in doc.tables:
        if table.prov:
            page_no = table.prov[0].page_no
            try:
                table_md = table.export_to_markdown()
                if table_md.strip():
                    pages_text[page_no].append(table_md)
            except Exception:
                pass
    return pages_text


def extract_text_with_pages(path: str) -> List[Tuple[str, int]]:
    """
    Extract text from a PDF or DOCX file with page number tracking.
    Tries native text extraction first; falls back to OCR if no text found.

    Returns:
        List of (text, page_number) tuples, one entry per page that has content.
    """
    doc = _get_converter(ocr=False).convert(path).document
    pages_text = _extract_pages_from_doc(doc)

    if not pages_text:
        doc = _get_converter(ocr=True).convert(path).document
        pages_text = _extract_pages_from_doc(doc)

    return [
        ("\n".join(texts), page_no)
        for page_no, texts in sorted(pages_text.items())
        if texts
    ]


def chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> List[str]:
    """Legacy function: chunk text without page tracking."""
    chunks = []
    start = 0

    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if overlap >= max_chars:
        raise ValueError("overlap must be < max_chars")

    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end])

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def chunk_text_with_pages(text_pages: List[Tuple[str, int]],
                          max_chars: int = 1500,
                          overlap: int = 200) -> List[Tuple[str, int]]:
    """
    Chunk text from multiple pages, preserving page numbers.

    Chunks within each page independently so that every chunk is labeled
    with the page it actually came from.

    Args:
        text_pages: List of (text, page_number) tuples
        max_chars: Maximum characters per chunk
        overlap: Overlap between consecutive chunks within the same page

    Returns:
        List of (chunk_text, page_number) tuples.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if overlap >= max_chars:
        raise ValueError("overlap must be < max_chars")

    chunks = []

    for text, page_num in text_pages:
        text = text.strip()
        if not text:
            continue

        if len(text) <= max_chars:
            chunks.append((text, page_num))
        else:
            start = 0
            while start < len(text):
                end = min(len(text), start + max_chars)
                chunks.append((text[start:end].strip(), page_num))
                if end >= len(text):
                    break
                start = end - overlap

    return chunks
