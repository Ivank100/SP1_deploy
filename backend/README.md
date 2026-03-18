<!--
This file documents the backend service in more detail.
It covers backend setup, architecture, and development workflow.
-->

Backend structure:

- `api/`: FastAPI entrypoint, request models, middleware, and route handlers.
- `clients/`: External API clients.
- `core/`: Shared configuration and authentication primitives.
- `db/`: Database access and persistence helpers.
- `ingestion/`: File parsing, upload storage, transcription, and indexing.
- `services/`: Higher-level product logic like RAG, analytics, study materials, and flashcards.
- `utils/`: Small cross-cutting helpers that do not own business logic.

Suggested rule of thumb:

- If it talks HTTP, it belongs in `api/`.
- If it talks to Postgres directly, it belongs in `db/`.
- If it processes uploaded content into chunks/transcripts, it belongs in `ingestion/`.
- If it combines multiple layers into app behavior, it belongs in `services/`.
