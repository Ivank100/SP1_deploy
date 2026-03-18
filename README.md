# LectureSense

A comprehensive lecture management and Q&A system that helps students and instructors make sense of recorded lectures. Features include PDF/PPT/audio support, AI-powered Q&A, analytics, and multi-tenancy.

## Features

- 📄 **PDF & PPT Support**: Upload and extract text from PDFs and PowerPoint presentations
- 🎤 **Audio Transcription**: Transcribe audio lectures using free local Whisper or OpenAI Whisper API
- 💬 **AI-Powered Q&A**: Ask questions about lectures and get answers with citations
- 📊 **Instructor Analytics**: Track student queries, trends, and lecture health metrics
- 👥 **Multi-Tenancy**: Role-based access control (students, instructors)
- 🔐 **Authentication**: JWT-based user authentication and authorization
- 📚 **Course Management**: Organize lectures into courses
- 🎯 **Study Materials**: Auto-generate summaries, key points, and flashcards

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 12+ with pgvector extension
- (Optional) OpenAI API key for Whisper API (local Whisper is free and used by default)

## Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd SP1
```

### 2. Set Up Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# OpenAI-compatible API (Required)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_CHAT_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# OpenAI Whisper API (Optional - only needed if using Whisper API instead of local)
WHISPER_MODEL=whisper-1

# Database Configuration (Required)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lecturesense
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
PGVECTOR_DIM=1536

# File Storage
UPLOAD_DIR=uploads

# JWT Authentication (Required)
# Generate a secure key: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=your_secure_random_key_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

**Generate a secure JWT secret key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Set Up PostgreSQL with pgvector

Install PostgreSQL and the pgvector extension:

```bash
# On macOS (using Homebrew)
brew install postgresql
brew install pgvector

# On Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
# Follow pgvector installation instructions: https://github.com/pgvector/pgvector
```

Create the database:

```bash
createdb lecturesense
# Or using psql:
psql -U postgres
CREATE DATABASE lecturesense;
\c lecturesense
CREATE EXTENSION vector;
```

### 4. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

## Running the Application

### Start the Backend API

```bash
# From the root directory
python run_api.py
```

The API will be available at `http://localhost:8000`

If you change embedding models after lectures have already been ingested, re-embed the stored chunks:

```bash
python reembed_chunks.py
```

### Start the Frontend

```bash
# From the root directory
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Usage

### 1. Register/Login

- Navigate to `http://localhost:3000/auth/register`
- Create an account as a **student** or **instructor**
- Login at `http://localhost:3000/auth/login`

### 2. Create a Course

- After logging in, click "Create Course"
- Enter course name and description
- The course will be created and you'll be automatically enrolled

### 3. Upload Lectures

- Select a course
- Click "Upload Lecture"
- Upload PDF, PPT, or audio files
- Wait for processing to complete

### 4. Ask Questions

- Open a lecture
- Type your question in the chat
- Get AI-powered answers with citations

### 5. Instructor Analytics (Instructors Only)

- Navigate to "Analytics" from the home page
- View query clusters, trends, and lecture health metrics
- Filter by course and lecture

## API Endpoints

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info
- `GET /api/courses/` - List courses (filtered by user access)
- `POST /api/courses/` - Create a new course
- `POST /api/lectures` - Upload a lecture
- `GET /api/lectures/{id}` - Get lecture details
- `POST /api/queries/{lecture_id}` - Ask a question about a lecture
- `POST /api/queries/course/{course_id}` - Ask a question across a course
- `GET /api/instructor/analytics/*` - Instructor analytics endpoints

## Project Structure

```
SP1/
├── backend/
│   ├── api/              # FastAPI application
│   │   ├── routes/       # API endpoints
│   │   └── middleware/   # Auth middleware
│   ├── clients/          # External API clients
│   ├── core/             # Shared config/auth
│   ├── db/               # Database access layer
│   ├── ingestion/        # Lecture ingestion pipeline
│   ├── services/         # Business logic and generation
│   └── utils/            # Cross-cutting helpers
├── frontend/             # Next.js frontend
│   ├── app/              # Pages and routes
│   └── lib/              # API client
├── uploads/              # Uploaded files
├── requirements.txt      # Python dependencies
└── .env                  # Environment variables (not in git)
```

## Development

### Backend Development

```bash
# Run with auto-reload
python run_api.py

# Or with uvicorn directly
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend
npm run dev
```

## Security Notes

- **Never commit `.env` files** - They contain sensitive credentials
- `.env` is already in `.gitignore`
- Use `.env.example` as a template
- Generate strong JWT secret keys for production
- Use strong database passwords

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running: `pg_isready`
- Check database credentials in `.env`
- Ensure pgvector extension is installed: `psql -d lecturesense -c "CREATE EXTENSION IF NOT EXISTS vector;"`

### API Key Issues

- Verify all required environment variables are set
- Check `.env` file is in the root directory
- Restart the API server after changing `.env`

### Frontend Connection Issues

- Ensure backend is running on port 8000
- Check CORS settings in `backend/api/main.py`
- Verify API base URL in `frontend/lib/api.ts`

## License

[Your License Here]

## Contributing

[Contributing Guidelines Here]
