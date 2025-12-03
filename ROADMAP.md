# LectureSense Development Roadmap

## Current Status: v0 ✅ COMPLETE

**What v0 has:**
- ✅ PDF ingestion with PyMuPDF
- ✅ Text chunking with overlap
- ✅ Embedding generation (local sentence-transformers)
- ✅ PostgreSQL + pgvector storage
- ✅ RAG query with DeepSeek LLM
- ✅ Query history storage
- ✅ Local file storage

**What v0 is missing (from spec):**
- ❌ Page number citations in answers
- ❌ Lecture/file metadata tracking
- ❌ LlamaIndex integration
- ❌ Web interface
- ❌ Multi-lecture support

---

## v1: Citations & Lecture Management

**Goal:** Add proper citations and lecture tracking to match v0 spec requirements.

### 1.1 Database Schema Updates
- [ ] Create `lectures` table (id, original_name, file_path, page_count, status, created_at)
- [ ] Update `chunks` table to include `lecture_id`, `page_number` (replace `document_chunks`)
- [ ] Add foreign key relationship: `chunks.lecture_id → lectures.id`
- [ ] Migration script to convert existing `document_chunks` to new schema

### 1.2 PDF Processing Updates
- [ ] Track page numbers during PDF extraction
- [ ] Store page metadata with each chunk
- [ ] Update `pdf_utils.py` to return page-aware chunks: `List[Tuple[str, int]]` (text, page_num)
- [ ] Store lecture metadata in `lectures` table

### 1.3 Citation Generation
- [ ] Update `search_similar()` to return chunks with page numbers
- [ ] Modify `answer_question()` to include citation metadata
- [ ] Format citations in answer: "See pages 3, 5-6" or "See page 3"
- [ ] Update prompt to instruct LLM to reference page numbers

### 1.4 File Management
- [ ] Create `uploads/` directory structure
- [ ] Copy uploaded PDFs to `uploads/` with unique names
- [ ] Track file paths in `lectures.file_path`
- [ ] Add file cleanup utilities

**Files to modify:**
- `src/db.py` - New schema, migration
- `src/pdf_utils.py` - Page-aware extraction
- `src/rag_index.py` - Lecture creation, page tracking
- `src/rag_query.py` - Citation formatting
- `src/config.py` - Add UPLOAD_DIR

**Estimated effort:** 2-3 days

---

## v2: Web API (FastAPI Backend)

**Goal:** Create REST API for frontend integration.

### 2.1 FastAPI Setup
- [ ] Install FastAPI, uvicorn, python-multipart
- [ ] Create `src/api/` module structure
- [ ] Main app: `src/api/main.py`
- [ ] CORS configuration

### 2.2 File Upload Endpoint
- [ ] `POST /api/lectures/upload` - Accept PDF file
- [ ] Validate file type and size
- [ ] Save to `uploads/` directory
- [ ] Return lecture_id

### 2.3 Lecture Management Endpoints
- [ ] `GET /api/lectures` - List all lectures
- [ ] `GET /api/lectures/{lecture_id}` - Get lecture details
- [ ] `DELETE /api/lectures/{lecture_id}` - Delete lecture + chunks
- [ ] `GET /api/lectures/{lecture_id}/status` - Processing status

### 2.4 Query Endpoints
- [ ] `POST /api/lectures/{lecture_id}/query` - Ask question about specific lecture
- [ ] `GET /api/lectures/{lecture_id}/history` - Query history for lecture
- [ ] Return JSON with answer + citations

### 2.5 Background Processing
- [ ] `POST /api/lectures/{lecture_id}/process` - Trigger ingestion
- [ ] Use Celery or RQ for async processing
- [ ] Update lecture status: `processing` → `completed` / `failed`
- [ ] Webhook/websocket for status updates (optional)

**Files to create:**
- `src/api/main.py`
- `src/api/routes/lectures.py`
- `src/api/routes/queries.py`
- `src/api/models.py` (Pydantic schemas)
- `src/api/background.py` (worker tasks)

**Estimated effort:** 3-4 days

---

## v3: Basic Web Frontend (Next.js)

**Goal:** Simple web interface for students.

### 3.1 Next.js Setup
- [ ] Initialize Next.js project in `frontend/`
- [ ] Configure API client to connect to FastAPI backend
- [ ] Basic layout and routing

### 3.2 Lecture Dashboard
- [ ] `GET /lectures` - List all uploaded lectures
- [ ] Display lecture name, page count, status
- [ ] Upload button → file picker → POST to API
- [ ] Processing indicator

### 3.3 Lecture Viewer
- [ ] `GET /lectures/[id]` - Single lecture view
- [ ] Q&A interface: input box + submit
- [ ] Display answer with citations (highlighted page numbers)
- [ ] Query history sidebar

### 3.4 Basic UI Components
- [ ] Upload component
- [ ] Lecture list component
- [ ] Q&A chat interface
- [ ] Citation display component

**Files to create:**
- `frontend/` directory structure
- `frontend/app/lectures/page.tsx`
- `frontend/app/lectures/[id]/page.tsx`
- `frontend/components/` (reusable components)

**Estimated effort:** 4-5 days

---

## v4: Multi-Lecture Search & Course Management

**Goal:** Support multiple lectures and cross-lecture search.

### 4.1 Course & Lecture Hierarchy
- [x] Create `courses` table (id, name, description, created_at)
- [x] Add `lectures.course_id` foreign key
- [x] Update API: `GET /api/courses`, `POST /api/courses/{id}/lectures`

### 4.2 Cross-Lecture Search
- [x] Update `search_similar()` to accept optional `lecture_id` filter
- [x] `POST /api/courses/{course_id}/query` - Search across all lectures
- [x] Return results with lecture name + page number
- [x] Citation format: "See Lecture 1, page 3"

### 4.3 Lecture Selection in UI
- [x] Course selector in frontend
- [x] Filter queries by lecture or search all
- [x] Display which lecture(s) contributed to answer

**Files to modify:**
- `src/db.py` - Courses table
- `src/api/routes/courses.py` - New endpoints
- `frontend/` - Course selection UI

**Estimated effort:** 2-3 days

---

## v5: Summaries & Flashcards Generation

**Goal:** Generate study materials automatically.

### 5.1 Summary Generation
- [x] `POST /api/lectures/{lecture_id}/summarize`
- [x] Retrieve top chunks (or all chunks)
- [x] Prompt DeepSeek: "Summarize this lecture content..."
- [x] Store summary in `lectures.summary`
- [x] Cache summaries (regenerate on lecture update)

### 5.2 Key Points Extraction
- [x] `POST /api/lectures/{lecture_id}/key-points`
- [x] Use LLM to extract 5-10 key points
- [x] Store in `lectures.key_points` (JSON array)

### 5.3 Flashcard Generation
- [x] `POST /api/lectures/{lecture_id}/flashcards`
- [x] Create `flashcards` table (id, lecture_id, front, back, page_number)
- [x] Use LLM to generate Q&A pairs from chunks
- [x] Return JSON array of flashcards
- [x] Frontend: flashcard study interface

**Files to create:**
- `src/api/routes/study_materials.py`
- `src/db.py` - Flashcards table
- `frontend/components/Flashcards.tsx`

**Estimated effort:** 3-4 days

---

## v6: Audio Transcription (Whisper)

**Goal:** Support audio lecture files.

### 6.1 Audio File Support
- [x] Update upload endpoint to accept audio files (.mp3, .wav, .m4a)
- [x] Store audio files in `uploads/audio/`
- [x] Add `lectures.file_type` enum: 'pdf', 'audio', 'slides'

### 6.2 Whisper Integration
- [x] Integrate OpenAI Whisper API (or local Whisper)
- [x] `POST /api/lectures/{lecture_id}/transcribe`
- [x] Generate transcript with timestamps
- [x] Store transcript in `lectures.transcript` (JSON with segments)

### 6.3 Timestamp Citations
- [x] Update chunking to include timestamp ranges
- [x] Add `chunks.timestamp_start`, `chunks.timestamp_end`
- [x] Citation format: "See 12:34 - 15:20" or "See 12:34"
- [x] Frontend: click timestamp to jump in audio player

### 6.4 Audio Player
- [x] Frontend audio player component
- [x] Sync transcript display with playback
- [x] Highlight current segment

**Files to create:**
- `src/audio_utils.py` - Whisper integration
- `src/api/routes/audio.py`
- `frontend/components/AudioPlayer.tsx`

**Estimated effort:** 4-5 days

---

## v7: Slide/PPT Support

**Goal:** Process PowerPoint and slide files.

### 7.1 Slide File Parsing
- [x] Support .pptx, .ppt files
- [x] Use `python-pptx` or similar library
- [x] Extract text + slide numbers
- [ ] Store slide images (optional)

### 7.2 Slide Citations
- [x] Add slide-aware citations (reuse `page_number` for slide numbers)
- [x] Citation format: "See slide 5" or "See slides 3-4"
- [ ] Frontend: display slide thumbnails with citations

### 7.3 Slide Viewer
- [x] Frontend slide viewer component
- [x] Click citation → jump to slide
- [x] Display slide text content

**Files to create:**
- `src/slide_utils.py`
- `frontend/components/SlideViewer.tsx`

**Estimated effort:** 3-4 days

---

## v8: Instructor Analytics Dashboard ✅ COMPLETE

**Goal:** Analytics for instructors to understand student needs.

### 8.1 Query Analytics
- [x] Link `query_history` to `lecture_id` (already done in v1)
- [x] `GET /api/instructor/analytics/query-clusters`
- [x] Use clustering (K-means or similar) on question embeddings
- [x] Return topic clusters with question counts

### 8.2 Trend Analysis
- [x] `GET /api/instructor/analytics/trends`
- [x] Group queries by time period (day/week)
- [x] Identify trending topics
- [x] Detect confusion patterns (repeated questions)

### 8.3 Lecture Health Metrics
- [x] `GET /api/instructor/analytics/lecture-health`
- [x] Query count per lecture
- [x] Average question complexity
- [x] Most confusing topics (from clusters)

### 8.4 Instructor UI
- [x] New route: `/instructor/dashboard`
- [x] Charts: query trends, topic clusters, lecture metrics
- [x] Table: all student questions with filters

**Files created:**
- `src/api/routes/instructor.py`
- `src/analytics.py` - Clustering logic
- `frontend/app/instructor/page.tsx`

**Estimated effort:** 5-6 days

---

## v9: User Authentication & Multi-Tenancy ✅ COMPLETE

**Goal:** Support multiple users and courses.

### 9.1 Authentication
- [x] JWT-based auth (python-jose)
- [x] User registration/login endpoints
- [x] Password hashing (bcrypt via passlib)
- [x] Role-based access: `student`, `instructor`, `admin`

### 9.2 User Management
- [x] `users` table (id, email, password_hash, role, created_at)
- [x] `user_courses` junction table (many-to-many)
- [x] Update all tables to include `created_by` (user_id)

### 9.3 Access Control
- [x] Students can only access their courses
- [x] Instructors can see all student queries in their courses
- [x] API middleware for authentication

### 9.4 Frontend Auth
- [x] Login/register pages
- [x] JWT token storage (localStorage)
- [x] Protected routes
- [x] User info display and logout

**Files created:**
- `src/api/routes/auth.py`
- `src/api/middleware/auth.py`
- `src/auth_utils.py`
- `frontend/app/auth/login/page.tsx`
- `frontend/app/auth/register/page.tsx`

**Estimated effort:** 4-5 days

---

## v10: Production Deployment

**Goal:** Deploy to production with Docker and cloud services.

### 10.1 Docker Setup
- [ ] `Dockerfile` for backend
- [ ] `Dockerfile` for frontend
- [ ] `docker-compose.yml` (backend, frontend, postgres, redis)
- [ ] Environment variable management

### 10.2 Background Workers
- [ ] Celery or RQ worker for PDF/audio processing
- [ ] Redis for task queue
- [ ] Worker Docker container

### 10.3 Object Storage
- [ ] Migrate from local `uploads/` to S3 (or compatible)
- [ ] Update file paths to S3 URLs
- [ ] Presigned URLs for secure access

### 10.4 Deployment
- [ ] EC2/Linode/VPS setup
- [ ] Nginx reverse proxy
- [ ] SSL/HTTPS (Let's Encrypt)
- [ ] Database backups
- [ ] Monitoring (optional: Sentry, logs)

**Files to create:**
- `Dockerfile`, `docker-compose.yml`
- `deploy/` scripts
- `.env.production` template

**Estimated effort:** 5-7 days

---

## v11: Advanced Features (Future)

### 11.1 LlamaIndex Integration
- [ ] Replace custom RAG with LlamaIndex
- [ ] Use LlamaIndex query engines
- [ ] Better prompt engineering

### 11.2 Real-time Collaboration
- [ ] WebSocket support for live updates
- [ ] Shared lecture sessions
- [ ] Collaborative annotations

### 11.3 Advanced Search
- [ ] Full-text search (PostgreSQL)
- [ ] Hybrid search (vector + keyword)
- [ ] Search filters (date, course, lecture)

### 11.4 Export Features
- [ ] Export summaries to PDF
- [ ] Export flashcards to Anki format
- [ ] Export query history

### 11.5 Mobile App
- [ ] React Native app
- [ ] Offline support
- [ ] Push notifications

---

## Priority Recommendations

**Immediate (v1):** Citations are critical for v0 spec completion
**Short-term (v2-v3):** Web interface makes it usable
**Medium-term (v4-v6):** Multi-lecture and audio expand use cases
**Long-term (v7-v10):** Production-ready features

---

## Technical Debt to Address

1. **Replace local embeddings** with DeepSeek embedding API (currently using sentence-transformers)
2. **Add error handling** throughout (try/except, validation)
3. **Add logging** (structured logging with levels)
4. **Add tests** (unit tests, integration tests)
5. **Documentation** (API docs, user guide)
6. **Performance optimization** (chunking strategy, index tuning)


