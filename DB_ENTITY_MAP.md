# DB Entity Map

Small helper for tracing each main data entity through the app.

## Core Pattern

1. Schema and migrations: `backend/db/schema.py`
2. DB access layer: `backend/db/*.py`
3. Business logic / orchestration: `backend/services/*.py` and `backend/ingestion/*.py`
4. API handlers: `backend/api/routes/**/*.py`
5. Frontend API client: `frontend/lib/api.ts`

## Users

- Schema: `backend/db/schema.py`
  - table: `users`
- DB helpers: `backend/db/users.py`
  - create/get user
- Auth/token logic: `backend/core/auth.py`
- Backend handlers: `backend/api/middleware/auth.py`
- API routes: `backend/api/routes/auth.py`

## Courses

- Schema: `backend/db/schema.py`
  - table: `courses`
- DB helpers: `backend/db/courses.py`
  - create/list/get/delete/join-code visibility
- Backend handlers: `backend/api/routes/courses/shared.py`
- API routes:
  - `backend/api/routes/courses/read.py`
  - `backend/api/routes/courses/write.py`
- Frontend client:
  - `frontend/lib/api.ts`
  - hooks/pages around course views: `frontend/hooks/useCoursePage.ts`, `frontend/hooks/useCourseDetailPage.tsx`, `frontend/hooks/useHomePage.ts`

## Course Membership

- Schema: `backend/db/schema.py`
  - table: `user_courses`
- DB helpers:
  - `backend/db/users.py`
  - `backend/db/courses.py`
- Backend handlers:
  - `backend/api/routes/courses/shared.py`
  - `backend/api/routes/courses/students.py`
- API routes:
  - student/course assignment and leave flows in `backend/api/routes/courses/students.py`

## Course Instructors

- Schema: `backend/db/schema.py`
  - table: `course_instructors`
- DB helpers: `backend/db/courses.py`
  - assignment + visibility logic
- Backend handlers:
  - consumed indirectly by course creation and instructor visibility
- API routes:
  - currently no dedicated admin API surface
  - auto-assignment on course creation: `backend/api/routes/courses/write.py`

## Announcements

- Schema: `backend/db/schema.py`
  - table: `course_announcements`
- DB access:
  - direct SQL in `backend/api/routes/courses/announcements.py`
- API routes:
  - `backend/api/routes/courses/announcements.py`
- Frontend:
  - `frontend/lib/api.ts`
  - `frontend/hooks/useCourseDetailPage.tsx`

## Lecture Upload Requests

- Schema: `backend/db/schema.py`
  - table: `lecture_upload_requests`
- DB helpers: `backend/db/upload_requests.py`
- Backend handlers:
  - `backend/api/routes/courses/shared.py`
  - file lifecycle helpers in `backend/ingestion/files.py`
- API routes:
  - `backend/api/routes/courses/uploads.py`
- Frontend:
  - `frontend/lib/api.ts`
  - `frontend/components/courses/FileUpload.tsx`
  - `frontend/hooks/useCourseDetailPage.tsx`

## Lectures

- Schema: `backend/db/schema.py`
  - table: `lectures`
- DB helpers: `backend/db/lectures.py`
- Backend handlers:
  - ingestion: `backend/ingestion/indexer.py`
  - shared lecture helpers: `backend/api/routes/lectures/shared.py`
- API routes:
  - `backend/api/routes/lectures/read.py`
  - `backend/api/routes/lectures/write.py`
  - `backend/api/routes/lectures/files.py`
- Frontend:
  - `frontend/lib/api.ts`
  - `frontend/hooks/useLecturePage.ts`
  - `frontend/hooks/useLectureWorkspace.ts`

## Chunks

- Schema: `backend/db/schema.py`
  - table: `chunks`
- DB helpers: `backend/db/chunks.py`
- Backend handlers:
  - ingestion writes: `backend/ingestion/indexer.py`
  - audio transcription refresh: `backend/api/routes/audio.py`
  - retrieval/search: `backend/services/rag/service.py`
- API routes:
  - not exposed directly as CRUD
  - consumed by lecture, slides, audio, and query flows

## Lecture Resources

- Schema: `backend/db/schema.py`
  - table: `lecture_resources`
- DB helpers: `backend/db/lectures.py`
- API routes:
  - `backend/api/routes/lectures/resources.py`
- Frontend:
  - `frontend/lib/api.ts`
  - `frontend/hooks/useLectureWorkspace.ts`

## Query History

- Schema: `backend/db/schema.py`
  - table: `query_history`
- DB helpers: `backend/db/queries.py`
- Backend handlers:
  - write path from `backend/services/rag/service.py`
  - analytics read paths in `backend/services/analytics/*.py`
- API routes:
  - `backend/api/routes/queries.py`
  - `backend/api/routes/courses/analytics.py`
  - `backend/api/routes/instructor.py`
- Frontend:
  - `frontend/lib/api.ts`
  - `frontend/hooks/useLectureQuestions.ts`
  - `frontend/hooks/useInstructorDashboardPage.ts`

## Flashcard Sets

- Schema: `backend/db/schema.py`
  - table: `flashcard_sets`
- DB helpers: `backend/db/flashcards.py`
- Backend handlers:
  - generation pipeline in `backend/services/flashcards/`
- API routes:
  - `backend/api/routes/study_materials.py`

## Flashcards

- Schema: `backend/db/schema.py`
  - table: `flashcards`
- DB helpers: `backend/db/flashcards.py`
- Backend handlers:
  - generation pipeline in `backend/services/flashcards/`
- API routes:
  - `backend/api/routes/study_materials.py`
- Frontend:
  - `frontend/lib/api.ts`
  - `frontend/components/reusable/Flashcards.tsx`
  - `frontend/hooks/useLectureWorkspace.ts`

## Study Materials Stored On Lectures

- Schema: `backend/db/schema.py`
  - columns on `lectures`: `summary`, `key_points`, `transcript`
- DB helpers: `backend/db/lectures.py`
- Backend handlers:
  - summaries/key points: `backend/services/study_materials/`
  - transcript/audio: `backend/ingestion/audio.py`, `backend/api/routes/audio.py`
- API routes:
  - `backend/api/routes/study_materials.py`
  - `backend/api/routes/audio.py`
  - `backend/api/routes/slides.py`

## Legacy / Drift Objects

- `document_chunks`
  - retired legacy table from the old v0 schema
  - no longer created by the current app
- `course_sections`, `section_groups`
  - removed as live DB drift not used by the current app code
- `user_courses.section_id`, `user_courses.group_id`
  - removed as live DB drift not used by the current app code

## Fastest Grep Shortcuts

- Find schema definition:
  - `rg "CREATE TABLE IF NOT EXISTS <table>" backend/db/schema.py`
- Find DB helpers:
  - `rg "<table>|<entity>" backend/db`
- Find backend handlers:
  - `rg "<entity>" backend/services backend/ingestion backend/api/routes`
- Find frontend callers:
  - `rg "<entity>|<endpoint>" frontend`
