# v1 Implementation Complete ✅

## What Was Implemented

### 1. Database Schema (v1)
- ✅ Created `lectures` table (id, original_name, file_path, page_count, status, created_at)
- ✅ Created `chunks` table (id, lecture_id, page_number, chunk_index, text, embedding)
- ✅ Updated `query_history` to include `lecture_id`
- ✅ Added proper indexes for performance
- ✅ Kept `document_chunks` table for backward compatibility

### 2. File Management
- ✅ Created `src/file_utils.py` for uploads directory management
- ✅ Files are now saved to `uploads/` with unique names
- ✅ File paths stored in database

### 3. Page Number Tracking
- ✅ Updated `pdf_utils.py` with `extract_text_with_pages()` and `chunk_text_with_pages()`
- ✅ Chunks now preserve page numbers
- ✅ Each chunk knows which page it came from

### 4. Citation Generation
- ✅ Created `src/citation_utils.py` with `format_citations()` function
- ✅ Formats page numbers: "See page 3" or "See pages 3, 5-7"
- ✅ Citations automatically appended to answers

### 5. Updated Functions
- ✅ `insert_lecture()` - Create lecture records
- ✅ `insert_chunks()` - Now accepts lecture_id and page numbers
- ✅ `search_similar()` - Returns (text, page_number, lecture_id) tuples
- ✅ `answer_question()` - Now accepts lecture_id and returns citations
- ✅ `update_lecture_status()` - Track processing status

### 6. Updated CLI
- ✅ `rag_index.py` - Uses new schema, saves files, tracks pages
- ✅ `rag_query.py` - Shows available lectures, formats citations

### 7. Migration Script
- ✅ Created `migrate_v0_to_v1.py` to convert old data

## New Files Created

1. `src/file_utils.py` - File upload management
2. `src/citation_utils.py` - Citation formatting
3. `src/migrate_v0_to_v1.py` - Data migration script

## Files Modified

1. `src/config.py` - Added UPLOAD_DIR
2. `src/db.py` - New schema and functions
3. `src/pdf_utils.py` - Page-aware extraction
4. `src/rag_index.py` - Uses new schema
5. `src/rag_query.py` - Citations and lecture selection

## Usage

### Ingest a PDF (v1):
```bash
python -m src.rag_index ~/Desktop/CA-Lecture-01.pdf
```

This will:
- Save PDF to `uploads/` directory
- Create lecture record
- Extract text with page numbers
- Chunk and embed
- Store with page metadata

### Query with Citations:
```bash
python -m src.rag_query
```

This will:
- Show available lectures
- Let you select a lecture (or search all)
- Return answers with page citations

### Migrate Old Data:
```bash
python -m src.migrate_v0_to_v1
```

## Database Schema

### lectures
- `id` (SERIAL PRIMARY KEY)
- `original_name` (TEXT) - Original filename
- `file_path` (TEXT) - Path in uploads/
- `page_count` (INT) - Number of pages
- `status` (TEXT) - 'processing', 'completed', 'failed'
- `created_at` (TIMESTAMP)

### chunks
- `id` (SERIAL PRIMARY KEY)
- `lecture_id` (INT) - Foreign key to lectures
- `page_number` (INT) - Page number (1-indexed)
- `chunk_index` (INT) - Chunk order within page
- `text` (TEXT) - Chunk content
- `embedding` (vector(1536)) - Embedding vector

### query_history
- `id` (SERIAL PRIMARY KEY)
- `lecture_id` (INT) - Optional foreign key
- `question` (TEXT)
- `answer` (TEXT)
- `created_at` (TIMESTAMP)

## Breaking Changes

⚠️ **Note:** The old `document_chunks` table is still present for backward compatibility, but new code uses the `chunks` table.

If you have existing data:
1. Run the migration script: `python -m src.migrate_v0_to_v1`
2. Or start fresh with new PDFs

## Next Steps (v2)

Now that v1 is complete, you can:
- Build the FastAPI web backend (v2)
- Or add more features like summaries/flashcards (v5)
- Or add multi-lecture search (v4)

See `ROADMAP.md` for the full development plan.

