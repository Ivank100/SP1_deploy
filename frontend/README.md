<!--
This file documents the frontend app setup and local workflow.
It is the quick reference for running or extending the Next.js client.
-->

# LectureSense Frontend

Next.js frontend for LectureSense - AI-powered lecture Q&A system.

## Features

- 📄 Upload PDF lectures
- 💬 Ask questions with AI-powered answers
- 📚 View citations with page numbers
- 📝 Query history
- 🎨 Clean, modern UI inspired by NotebookLM

## Setup

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   # or
   yarn install
   ```

2. **Configure API URL:**
   Create `.env.local` file:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Run development server:**
   ```bash
   npm run dev
   # or
   yarn dev
   ```

4. **Open in browser:**
   http://localhost:3000

## Project Structure

```
frontend/
├── app/              # Next.js app directory
│   ├── page.tsx     # Home page (lecture list)
│   └── lectures/    # Lecture pages
├── components/       # React components
│   ├── FileUpload.tsx
│   └── LectureList.tsx
└── lib/             # Utilities
    └── api.ts       # API client
```

## API Integration

The frontend connects to the FastAPI backend. Make sure the backend is running on `http://localhost:8000` (or update `NEXT_PUBLIC_API_URL`).

## Build for Production

```bash
npm run build
npm start
```

