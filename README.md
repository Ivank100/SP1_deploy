# NotebookLM Clone (RAG Demo)

Simple RAG (Retrieval-Augmented Generation) app that:
- Ingests PDFs
- Stores embeddings in PostgreSQL with pgvector
- Answers questions using an LLM via OpenRouter

## Setup

### 1. Clone & enter folder

```bash
git clone https://github.com/<your-username>/notebooklm-clone.git
cd notebooklm-clone
Create venv & install deps:
python -m venv venv
source venv/bin/activate.fish   # fish shell
pip install -r requirements.txt
set -x DEEPSEEK_API_KEY "YOUR_OPENROUTER_API_KEY"
set -x DEEPSEEK_BASE_URL "https://openrouter.ai/api/v1"

set -x PG_HOST "localhost"
set -x PG_PORT "5432"
set -x PG_DB   "your_db_name"
set -x PG_USER "your_db_user"
set -x PG_PASS "your_db_password"
4. Usage
python -m src.rag_index uploads/Story.pdf
python -m src.rag_query
Question (empty to quit): Summarize the story.

