<!--
This file is the main project guide for LectureSense.
It explains the product, stack, setup steps, and available features.
-->

# LectureSense

LectureSense is a full-stack lecture workspace for students and instructors. It supports course-based lecture uploads, AI question answering over lecture content, instructor analytics, study materials, and audio/slides workflows.

## What The Current Codebase Supports

- Course-based organization with join codes
- Student and instructor accounts
- PDF, slide deck (`.ppt`, `.pptx`), and audio lecture ingestion
- AI Q&A over a single lecture or across a course
- Query history with citations
- Instructor analytics for courses and lectures
- Study materials:
  - summaries
  - key points
  - flashcards
- Audio transcription
- Lecture resources and file replacement
- Student upload requests with instructor/TA approval flow

## Stack

- Backend: FastAPI + PostgreSQL + pgvector
- Frontend: Next.js 14 + React 18 + TypeScript
- AI / ML:
  - OpenAI-compatible chat + embeddings API
  - local Whisper or Whisper API for transcription
  - scikit-learn for analytics clustering
  - Docling for PDF/slide extraction

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 12+ with `pgvector`

## Environment Variables

Create a root `.env` file.

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_CHAT_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
WHISPER_MODEL=whisper-1

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lecturesense
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
PGVECTOR_DIM=1536

UPLOAD_DIR=uploads
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Notes:

- `OPENAI_API_KEY` is currently required by the backend config at startup.
- `NEXT_PUBLIC_API_URL` is read by the frontend.
- The backend will create/update its expected schema on startup.

## Setup

### 1. Clone

```bash
git clone <your-repo-url>
cd SP1
```

### 2. Install Python dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Prepare PostgreSQL

Create the database and enable `pgvector`.

```sql
CREATE DATABASE lecturesense;
\c lecturesense
CREATE EXTENSION vector;
```

## Run The App

### Backend

```bash
python run_api.py
```

Backend URLs:

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### Frontend

```bash
cd frontend
npm run dev
```

Frontend URL:

- App: `http://localhost:3000`

## Useful Commands

Re-embed stored chunks after changing embedding models:

```bash
python -m backend.scripts.reembed_chunks
```

Frontend production build:

```bash
cd frontend
npm run build
npm start
```

## Main User Flows

### Students

- register and log in
- join a course by code
- open a lecture and ask questions
- ask course-level questions
- view generated study materials
- submit upload requests to a course

### Instructors

- create courses
- upload lectures directly
- review student upload requests
- manage enrolled students / TAs
- post announcements
- review course and lecture analytics

## API Surface Overview

### Auth

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

### Courses

- `GET /api/courses/`
- `POST /api/courses/`
- `DELETE /api/courses/{course_id}`
- `POST /api/courses/join`
- `POST /api/courses/{course_id}/query`
- `GET /api/courses/{course_id}/analytics`
- `GET /api/courses/{course_id}/questions/export`

### Course membership / announcements / uploads

- `POST /api/courses/{course_id}/students`
- `DELETE /api/courses/{course_id}/students/{student_id}`
- `PATCH /api/courses/{course_id}/students/{student_id}`
- `GET /api/courses/{course_id}/students`
- `DELETE /api/courses/{course_id}/leave`
- `POST /api/courses/{course_id}/announcements`
- `GET /api/courses/{course_id}/announcements`
- `POST /api/courses/{course_id}/lectures`
- `POST /api/courses/{course_id}/upload-requests`
- `GET /api/courses/{course_id}/upload-requests`
- `GET /api/courses/{course_id}/upload-requests/mine`
- `POST /api/courses/{course_id}/upload-requests/{request_id}/approve`
- `POST /api/courses/{course_id}/upload-requests/{request_id}/reject`
- `DELETE /api/courses/{course_id}/upload-requests/{request_id}`

### Lectures

- `GET /api/lectures/`
- `POST /api/lectures/upload`
- `GET /api/lectures/{lecture_id}`
- `GET /api/lectures/{lecture_id}/status`
- `GET /api/lectures/{lecture_id}/download`
- `PATCH /api/lectures/{lecture_id}/rename`
- `PATCH /api/lectures/{lecture_id}/archive`
- `DELETE /api/lectures/{lecture_id}`
- `POST /api/lectures/{lecture_id}/replace`

### Lecture Q&A / media / resources / study materials

- `POST /api/lectures/{lecture_id}/query`
- `GET /api/lectures/{lecture_id}/history`
- `GET /api/lectures/{lecture_id}/analytics`
- `POST /api/lectures/{lecture_id}/transcribe`
- `GET /api/lectures/{lecture_id}/transcript`
- `GET /api/lectures/{lecture_id}/slides`
- `GET /api/lectures/{lecture_id}/resources`
- `POST /api/lectures/{lecture_id}/resources`
- `DELETE /api/lectures/{lecture_id}/resources/{resource_id}`
- `GET /api/lectures/{lecture_id}/study-materials`
- `POST /api/lectures/{lecture_id}/summarize`
- `POST /api/lectures/{lecture_id}/key-points`
- `POST /api/lectures/{lecture_id}/flashcards`
- `POST /api/lectures/{lecture_id}/flashcards/generate`
- `POST /api/lectures/{lecture_id}/flashcards/regenerate`
- `GET /api/lectures/{lecture_id}/flashcards/latest`
- `GET /api/lectures/{lecture_id}/flashcards/sets/{set_id}`

### Instructor analytics

- `GET /api/instructor/analytics/query-clusters`
- `GET /api/instructor/analytics/trends`
- `GET /api/instructor/analytics/lecture-health`
- `GET /api/instructor/queries`

## Project Structure

```text
SP1/
├── backend/
│   ├── api/
│   │   ├── app.py
│   │   ├── main.py
│   │   ├── dependencies/
│   │   ├── routers/
│   │   ├── schemas/
│   │   └── services/
│   ├── clients/
│   ├── core/
│   ├── db/
│   ├── ingestion/
│   ├── scripts/
│   ├── services/
│   └── utils/
├── docs/
│   └── DB_ENTITY_MAP.md
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   └── lib/
├── requirements.txt
└── run_api.py
```

## Developer Notes

- The backend now uses `backend/api/app.py` as the actual FastAPI assembly point.
- The DB entity tracing helper lives at [`DB_ENTITY_MAP.md`](DB_ENTITY_MAP.md).
- The legacy `document_chunks` schema path has been retired.
- `npm run lint` is still not fully wired for non-interactive use until an ESLint config is added.

## Current Caveats

- Authentication is currently a simple bearer-token flow implemented in code, not a production-ready hardened auth setup.
- TA behavior exists partly through `user_courses.role`, but some app-level role handling is still instructor/student-centric.
- CORS is currently open (`allow_origins=["*"]`) in the backend.
