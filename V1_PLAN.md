# v1 Implementation Plan: Citations & Lecture Management

## Overview
v1 adds the missing pieces from the v0 spec: **page number citations** and **proper lecture tracking**.

## Current Gaps Analysis

### What's Missing from v0 Spec:
1. ❌ **Citations**: Answers don't include page numbers
2. ❌ **Lecture metadata**: No `lectures` table, just `doc_id` strings
3. ❌ **Page tracking**: Chunks don't store which page they came from
4. ❌ **File management**: PDFs aren't stored in `uploads/` directory

## v1 Tasks Breakdown

### Task 1: Database Schema Migration (2-3 hours)

**Create new tables:**
```sql
CREATE TABLE IF NOT EXISTS lectures (
    id SERIAL PRIMARY KEY,
    original_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    page_count INT DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'processing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    lecture_id INT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    page_number INT NOT NULL,
    chunk_index INT NOT NULL,
    text TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    UNIQUE(lecture_id, page_number, chunk_index)
);
```

**Migration script:**
- Read existing `document_chunks`
- Create a `lectures` entry for each unique `doc_id`
- Migrate chunks to new schema (assign page_number = 0 for now, or try to infer)

### Task 2: Update PDF Processing (2-3 hours)

**Modify `pdf_utils.py`:**
```python
def extract_text_with_pages(path: str) -> List[Tuple[str, int]]:
    """Returns list of (text, page_number) tuples."""
    doc = fitz.open(path)
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        pages.append((text, page_num))
    doc.close()
    return pages

def chunk_text_with_pages(text_pages: List[Tuple[str, int]], 
                          max_chars: int = 1500, 
                          overlap: int = 200) -> List[Tuple[str, int]]:
    """Returns list of (chunk_text, page_number) tuples."""
    # Chunking logic that preserves page numbers
    # If chunk spans pages, use the starting page number
```

### Task 3: Update Database Functions (2-3 hours)

**Modify `db.py`:**
- `insert_lecture()` - Create lecture record
- `insert_chunks()` - Accept lecture_id and page_number
- `search_similar()` - Return chunks with page_number and lecture_id
- Update `init_schema()` to create new tables

### Task 4: Update RAG Query (2-3 hours)

**Modify `rag_query.py`:**
- Update `answer_question()` to accept `lecture_id` parameter
- Collect page numbers from retrieved chunks
- Format citations: "See pages 3, 5-6" or "See page 3"
- Update prompt to include citation instructions

**Example citation formatting:**
```python
def format_citations(page_numbers: List[int]) -> str:
    """Format [3, 5, 6, 7] -> 'See pages 3, 5-7'"""
    if not page_numbers:
        return ""
    sorted_pages = sorted(set(page_numbers))
    # Group consecutive pages: [3, 5, 6, 7] -> ["3", "5-7"]
    # Return "See pages 3, 5-7"
```

### Task 5: File Management (1-2 hours)

**Create `src/file_utils.py`:**
```python
import os
import shutil
from pathlib import Path

UPLOAD_DIR = Path("uploads")

def save_uploaded_file(file_path: str, original_name: str) -> str:
    """Save uploaded file to uploads/ directory, return new path."""
    UPLOAD_DIR.mkdir(exist_ok=True)
    # Generate unique filename
    # Copy file
    # Return new path
```

**Update `rag_index.py`:**
- Copy PDF to `uploads/` before processing
- Create lecture record first
- Store file_path in lecture record

### Task 6: Update CLI Interface (1 hour)

**Modify `rag_index.py`:**
- Accept file path or copy from uploads
- Create lecture record
- Pass lecture_id to insert_chunks

**Modify `rag_query.py`:**
- Accept lecture_id as parameter or select active lecture
- Display citations in output

## Implementation Order

1. **Database schema** (Task 1) - Foundation
2. **File management** (Task 5) - Basic infrastructure
3. **PDF processing** (Task 2) - Core functionality
4. **Database functions** (Task 3) - Data layer
5. **RAG query** (Task 4) - User-facing feature
6. **CLI updates** (Task 6) - Integration

## Testing Checklist

- [ ] Upload PDF creates lecture record
- [ ] Chunks are stored with correct page numbers
- [ ] Query returns answer with page citations
- [ ] Citations are formatted correctly
- [ ] Multiple lectures can coexist
- [ ] Query history links to lecture_id

## Files to Modify

1. `src/db.py` - Schema + functions
2. `src/pdf_utils.py` - Page-aware extraction
3. `src/rag_index.py` - Lecture creation
4. `src/rag_query.py` - Citation formatting
5. `src/file_utils.py` - NEW: File management
6. `src/config.py` - Add UPLOAD_DIR

## Estimated Total Time: 10-14 hours (1.5-2 days)

## Next Steps After v1

Once v1 is complete, you'll have:
- ✅ Proper lecture management
- ✅ Page number citations
- ✅ File storage

Then move to **v2 (FastAPI)** to create a web API, or **v3 (Frontend)** if you prefer to build UI first.

