# src/db.py
import json
import psycopg
import psycopg.errors
from typing import List, Tuple, Optional, Any, Dict
from .config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS, PG_DIM

FILE_TYPES = ("pdf", "audio", "slides")

DEFAULT_COURSE_NAME = "General Course"
DEFAULT_COURSE_DESCRIPTION = "Default course for uncategorized lectures"

def get_conn():
    return psycopg.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
    )

def init_schema():
    """Initialize the database schema: enable pgvector extension and create document_chunks table."""
    with get_conn() as conn, conn.cursor() as cur:
        # Enable pgvector extension if not already enabled
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except psycopg.errors.FeatureNotSupported as e:
            print("\n[ERROR] pgvector extension is not installed in PostgreSQL.")
            print("\nTo install pgvector on macOS with Homebrew:")
            print("  1. Install pgvector: brew install pgvector")
            print("  2. Restart PostgreSQL: brew services restart postgresql@16")
            print("\nOr if using a different PostgreSQL installation:")
            print("  - Follow instructions at: https://github.com/pgvector/pgvector#installation")
            print("\nAfter installation, run this script again.")
            raise SystemExit(1) from e
        
        # Create document_chunks table if it doesn't exist
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS document_chunks (
                doc_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector({PG_DIM}) NOT NULL,
                PRIMARY KEY (doc_id, chunk_index)
            );
        """)
        
        # Create index for efficient similarity search
        cur.execute("""
            CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx 
            ON document_chunks 
            USING ivfflat (embedding vector_cosine_ops);
        """)

        # Create users table (v9 schema)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS users_email_idx ON users(email);
        """)

        # Create courses table (v4 schema)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INT REFERENCES users(id) ON DELETE SET NULL
            );
        """)
        
        # Create user_courses junction table (v9 schema)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_courses (
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                course_id INT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                role TEXT DEFAULT 'student',
                PRIMARY KEY (user_id, course_id)
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS user_courses_user_id_idx ON user_courses(user_id);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS user_courses_course_id_idx ON user_courses(course_id);
        """)
        
        # Add role column if it doesn't exist (migration)
        cur.execute("""
            ALTER TABLE user_courses
            ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'student';
        """)
        
        # Create course_instructors table for admin-assigned instructors
        cur.execute("""
            CREATE TABLE IF NOT EXISTS course_instructors (
                course_id INT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                instructor_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                assigned_by INT REFERENCES users(id) ON DELETE SET NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (course_id, instructor_id)
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS course_instructors_course_id_idx ON course_instructors(course_id);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS course_instructors_instructor_id_idx ON course_instructors(instructor_id);
        """)
        
        # Create lectures table (v1 schema)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lectures (
                id SERIAL PRIMARY KEY,
                original_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                page_count INT DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'processing',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                course_id INT REFERENCES courses(id) ON DELETE CASCADE,
                summary TEXT,
                key_points TEXT,
                file_type TEXT NOT NULL DEFAULT 'pdf',
                transcript JSONB,
                created_by INT REFERENCES users(id) ON DELETE SET NULL
            );
        """)
        
        # Add created_by column if it doesn't exist (migration)
        cur.execute("""
            ALTER TABLE lectures
            ADD COLUMN IF NOT EXISTS created_by INT REFERENCES users(id) ON DELETE SET NULL;
        """)
        
        # Add created_by column to courses if it doesn't exist (migration)
        cur.execute("""
            ALTER TABLE courses
            ADD COLUMN IF NOT EXISTS created_by INT REFERENCES users(id) ON DELETE SET NULL;
        """)

        # Ensure lecture metadata columns exist for legacy databases
        cur.execute("""
            ALTER TABLE lectures
            ADD COLUMN IF NOT EXISTS summary TEXT;
        """)
        cur.execute("""
            ALTER TABLE lectures
            ADD COLUMN IF NOT EXISTS key_points TEXT;
        """)
        cur.execute("""
            ALTER TABLE lectures
            ADD COLUMN IF NOT EXISTS file_type TEXT;
        """)
        cur.execute("""
            ALTER TABLE lectures
            ALTER COLUMN file_type SET DEFAULT 'pdf';
        """)
        cur.execute("""
            UPDATE lectures SET file_type = 'pdf' WHERE file_type IS NULL;
        """)
        cur.execute("""
            ALTER TABLE lectures
            ADD COLUMN IF NOT EXISTS transcript JSONB;
        """)

        # Ensure course_id column exists for legacy databases
        cur.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'lectures'
                AND column_name = 'course_id'
            );
        """)
        has_course_id = cur.fetchone()[0]

        if not has_course_id:
            cur.execute("""
                ALTER TABLE lectures
                ADD COLUMN course_id INT REFERENCES courses(id) ON DELETE CASCADE;
            """)
            print("[INFO] Added course_id column to lectures table")

        # Backfill null course references with the default course
        cur.execute("SELECT COUNT(*) FROM lectures WHERE course_id IS NULL;")
        missing_course_refs = cur.fetchone()[0]
        if missing_course_refs:
            default_course_id = _get_or_create_default_course(cur)
            cur.execute(
                "UPDATE lectures SET course_id = %s WHERE course_id IS NULL;",
                (default_course_id,),
            )
            print(f"[INFO] Linked {missing_course_refs} lecture(s) to default course")

        # Index for filtering lectures by course
        cur.execute("""
            CREATE INDEX IF NOT EXISTS lectures_course_id_idx
            ON lectures (course_id);
        """)
        
        # Create chunks table (v1 schema) - replaces document_chunks
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS chunks (
                id SERIAL PRIMARY KEY,
                lecture_id INT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
                page_number INT,
                chunk_index INT NOT NULL,
                text TEXT NOT NULL,
                embedding vector({PG_DIM}) NOT NULL,
                timestamp_start DOUBLE PRECISION,
                timestamp_end DOUBLE PRECISION,
                UNIQUE(lecture_id, chunk_index)
            );
        """)

        # Ensure new columns/indexes exist on chunks
        cur.execute("""
            DO $$
            BEGIN
                ALTER TABLE chunks DROP CONSTRAINT IF EXISTS chunks_lecture_id_page_number_chunk_index_key;
            EXCEPTION
                WHEN undefined_object THEN NULL;
            END$$;
        """)
        cur.execute("""
            ALTER TABLE chunks
            ADD COLUMN IF NOT EXISTS timestamp_start DOUBLE PRECISION;
        """)
        cur.execute("""
            ALTER TABLE chunks
            ADD COLUMN IF NOT EXISTS timestamp_end DOUBLE PRECISION;
        """)
        
        # Make page_number nullable (audio chunks don't have page numbers)
        cur.execute("""
            DO $$
            BEGIN
                ALTER TABLE chunks
                ALTER COLUMN page_number DROP NOT NULL;
            EXCEPTION
                WHEN OTHERS THEN
                    -- Column might already be nullable or constraint doesn't exist
                    NULL;
            END$$;
        """)
        cur.execute("""
            DO $$
            BEGIN
                ALTER TABLE chunks ADD CONSTRAINT chunks_lecture_chunk_index_unique UNIQUE (lecture_id, chunk_index);
            EXCEPTION
                WHEN duplicate_table THEN NULL;
                WHEN duplicate_object THEN NULL;
            END$$;
        """)
        
        # Create index for efficient similarity search on chunks
        cur.execute("""
            CREATE INDEX IF NOT EXISTS chunks_embedding_idx 
            ON chunks 
            USING ivfflat (embedding vector_cosine_ops);
        """)
        
        # Create index on lecture_id for faster filtering
        cur.execute("""
            CREATE INDEX IF NOT EXISTS chunks_lecture_id_idx 
            ON chunks (lecture_id);
        """)

        # Flashcards table for study materials
        cur.execute("""
            CREATE TABLE IF NOT EXISTS flashcards (
                id SERIAL PRIMARY KEY,
                lecture_id INT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
                front TEXT NOT NULL,
                back TEXT NOT NULL,
                page_number INT
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS flashcards_lecture_id_idx
            ON flashcards (lecture_id);
        """)
        
        # Create or update query_history table (v1)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Check if lecture_id column exists, add it if not (migration from v0)
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'query_history' 
                AND column_name = 'lecture_id'
            );
        """)
        has_lecture_id = cur.fetchone()[0]
        
        if not has_lecture_id:
            # Add lecture_id column to existing table
            cur.execute("""
                ALTER TABLE query_history 
                ADD COLUMN lecture_id INT REFERENCES lectures(id) ON DELETE SET NULL;
            """)
            print("[INFO] Added lecture_id column to query_history table")

        # Ensure course reference exists for cross-lecture queries
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'query_history' 
                AND column_name = 'course_id'
            );
        """)
        has_course_ref = cur.fetchone()[0]

        if not has_course_ref:
            cur.execute("""
                ALTER TABLE query_history 
                ADD COLUMN course_id INT REFERENCES courses(id) ON DELETE SET NULL;
            """)
            print("[INFO] Added course_id column to query_history table")
        
        # Create index on created_at for faster queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS query_history_created_at_idx 
            ON query_history (created_at DESC);
        """)
        
        # Create index on lecture_id for filtering
        # (Column will exist now - either it was already there or we just added it)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS query_history_lecture_id_idx 
            ON query_history (lecture_id);
        """)

        # Index for querying by course
        cur.execute("""
            CREATE INDEX IF NOT EXISTS query_history_course_id_idx 
            ON query_history (course_id);
        """)
        
        # Add user_id column if it doesn't exist (v9 migration)
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'query_history' 
                AND column_name = 'user_id'
            );
        """)
        has_user_id = cur.fetchone()[0]
        
        if not has_user_id:
            cur.execute("""
                ALTER TABLE query_history 
                ADD COLUMN user_id INT REFERENCES users(id) ON DELETE SET NULL;
            """)
            print("[INFO] Added user_id column to query_history table")
        
        # Create index on user_id for filtering
        cur.execute("""
            CREATE INDEX IF NOT EXISTS query_history_user_id_idx 
            ON query_history (user_id);
        """)
        
        conn.commit()
        print(f"[INFO] Database schema initialized (vector dimension: {PG_DIM})")

def _get_or_create_default_course(cur) -> int:
    """Ensure a default course exists and return its ID (expects existing cursor)."""
    cur.execute(
        """
        SELECT id FROM courses 
        WHERE name = %s
        ORDER BY id
        LIMIT 1
        """,
        (DEFAULT_COURSE_NAME,),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO courses (name, description)
        VALUES (%s, %s)
        RETURNING id
        """,
        (DEFAULT_COURSE_NAME, DEFAULT_COURSE_DESCRIPTION),
    )
    return cur.fetchone()[0]


def ensure_default_course() -> int:
    """Public helper to make sure a default fallback course exists."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        course_id = _get_or_create_default_course(cur)
        conn.commit()
        return course_id


def insert_lecture(
    original_name: str,
    file_path: str,
    page_count: int = 0,
    status: str = "processing",
    course_id: Optional[int] = None,
    file_type: str = "pdf",
    created_by: Optional[int] = None,
) -> int:
    """
    Create a new lecture record.
    
    Returns:
        lecture_id (int)
    """
    if file_type not in FILE_TYPES:
        raise ValueError(f"Unsupported file_type '{file_type}'. Expected one of {FILE_TYPES}")

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        if course_id is None:
            course_id = _get_or_create_default_course(cur)

        cur.execute(
            """
            INSERT INTO lectures (original_name, file_path, page_count, status, course_id, file_type, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (original_name, file_path, page_count, status, course_id, file_type, created_by),
        )
        lecture_id = cur.fetchone()[0]
        conn.commit()
        return lecture_id

def update_lecture_status(lecture_id: int, status: str):
    """Update lecture status (e.g., 'processing' -> 'completed')."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE lectures SET status = %s WHERE id = %s
            """,
            (status, lecture_id),
        )
        conn.commit()


def create_course(name: str, description: Optional[str] = None, created_by: Optional[int] = None) -> int:
    """Create a new course."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO courses (name, description, created_by)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (name, description, created_by),
        )
        course_id = cur.fetchone()[0]
        conn.commit()
        return course_id


def list_courses():
    """List all courses."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, description, created_at
            FROM courses
            ORDER BY created_at DESC
            """
        )
        return cur.fetchall()


def get_course(course_id: int):
    """Get a single course."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, description, created_at
            FROM courses
            WHERE id = %s
            """,
            (course_id,),
        )
        return cur.fetchone()


def delete_course(course_id: int):
    """Delete a course and cascade delete lectures."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM courses WHERE id = %s", (course_id,))
        conn.commit()


def get_chunks_for_lecture(
    lecture_id: int, limit: Optional[int] = None
) -> List[Tuple[str, Optional[int], Optional[float], Optional[float]]]:
    """Return ordered chunks (text, page, timestamp_start, timestamp_end) for a lecture."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        query = """
            SELECT text, page_number, timestamp_start, timestamp_end
            FROM chunks
            WHERE lecture_id = %s
            ORDER BY chunk_index
        """
        params: List[Any] = [lecture_id]
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        cur.execute(query, tuple(params))
        return cur.fetchall()


def save_lecture_summary(lecture_id: int, summary: str):
    """Persist a generated summary for a lecture."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE lectures SET summary = %s WHERE id = %s",
            (summary, lecture_id),
        )
        conn.commit()


def save_lecture_transcript(lecture_id: int, transcript: Dict[str, Any]):
    """Persist transcript JSON for a lecture."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE lectures SET transcript = %s WHERE id = %s",
            (json.dumps(transcript), lecture_id),
        )
        conn.commit()


def get_lecture_transcript(lecture_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve transcript JSON for a lecture."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT transcript FROM lectures WHERE id = %s", (lecture_id,))
        row = cur.fetchone()
        if not row or row[0] is None:
            return None
        value = row[0]
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return value


def save_lecture_key_points(lecture_id: int, key_points: List[str]):
    """Persist key points as JSON."""
    key_points_json = json.dumps(key_points)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE lectures SET key_points = %s WHERE id = %s",
            (key_points_json, lecture_id),
        )
        conn.commit()


def get_lecture_study_materials(lecture_id: int):
    """Fetch stored summary and key points for a lecture."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT summary, key_points FROM lectures WHERE id = %s",
            (lecture_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        summary, key_points_raw = row
        try:
            key_points = json.loads(key_points_raw) if key_points_raw else []
        except json.JSONDecodeError:
            key_points = []
        return {"summary": summary, "key_points": key_points}


def list_flashcards(lecture_id: int):
    """Return stored flashcards for a lecture."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, front, back, page_number
            FROM flashcards
            WHERE lecture_id = %s
            ORDER BY id
            """,
            (lecture_id,),
        )
        return cur.fetchall()


def replace_flashcards(lecture_id: int, cards: List[Tuple[str, str, Optional[int]]]):
    """Replace all flashcards for a lecture."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM flashcards WHERE lecture_id = %s", (lecture_id,))
        for front, back, page in cards:
            cur.execute(
                """
                INSERT INTO flashcards (lecture_id, front, back, page_number)
                VALUES (%s, %s, %s, %s)
                """,
                (lecture_id, front, back, page),
            )
        conn.commit()


def clear_chunks_for_lecture(lecture_id: int):
    """Delete all chunks for a lecture (used before reprocessing)."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE lecture_id = %s", (lecture_id,))
        conn.commit()

def insert_chunks(lecture_id: int, chunks_payload: List[Any], embeddings: List[List[float]]):
    """
    Insert chunks for a lecture. Payload entries can be tuples (text, page_number)
    or dictionaries containing text, page_number, timestamp_start, timestamp_end.
    """
    assert len(chunks_payload) == len(embeddings)
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        for chunk_index, (entry, emb) in enumerate(zip(chunks_payload, embeddings)):
            if isinstance(entry, dict):
                chunk_text = entry.get("text", "")
                page_num = entry.get("page_number")
                ts_start = entry.get("timestamp_start")
                ts_end = entry.get("timestamp_end")
            else:
                chunk_text, page_num = entry
                ts_start = None
                ts_end = None

            # Convert embedding list to pgvector string format: "[0.1,0.2,...]"
            vec_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
            cur.execute(
                """
                INSERT INTO chunks (lecture_id, page_number, chunk_index, text, embedding, timestamp_start, timestamp_end)
                VALUES (%s, %s, %s, %s, %s::vector, %s, %s)
                """,
                (lecture_id, page_num, chunk_index, chunk_text, vec_str, ts_start, ts_end),
            )
        conn.commit()

# Legacy function for backward compatibility
def insert_chunks_legacy(doc_id: str, chunks: List[str], embeddings: List[List[float]]):
    """Legacy function: insert chunks using old document_chunks schema."""
    assert len(chunks) == len(embeddings)
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            vec_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
            cur.execute(
                """
                INSERT INTO document_chunks (doc_id, chunk_index, content, embedding)
                VALUES (%s, %s, %s, %s::vector)
                """,
                (doc_id, i, chunk, vec_str),
            )
        conn.commit()


def search_similar(
    query_emb: List[float],
    top_k: int = 5,
    lecture_id: Optional[int] = None,
    course_id: Optional[int] = None,
) -> List[Tuple[str, Optional[int], int, str, str, Optional[float], Optional[float]]]:
    """
    Search for similar chunks using vector similarity.
    
    Args:
        query_emb: Query embedding vector
        top_k: Number of results to return
        lecture_id: Optional filter by specific lecture
        course_id: Optional filter by course (overrides lecture filter if lecture_id is None)
        
    Returns:
        List of (text, page_number, lecture_id, lecture_name, file_type, timestamp_start, timestamp_end) tuples
    """
    init_schema()
    vec_str = "[" + ",".join(f"{x:.6f}" for x in query_emb) + "]"

    with get_conn() as conn, conn.cursor() as cur:
        base_query = """
            SELECT
                c.text,
                c.page_number,
                c.lecture_id,
                l.original_name,
                l.file_type,
                c.timestamp_start,
                c.timestamp_end
            FROM chunks c
            JOIN lectures l ON c.lecture_id = l.id
        """
        params: List[Any] = []

        if lecture_id is not None:
            base_query += " WHERE c.lecture_id = %s"
            params.append(lecture_id)
        elif course_id is not None:
            base_query += " WHERE l.course_id = %s"
            params.append(course_id)

        base_query += " ORDER BY c.embedding <-> %s::vector LIMIT %s"
        params.extend([vec_str, top_k])

        cur.execute(base_query, tuple(params))
        return cur.fetchall()

# Legacy function for backward compatibility
def search_similar_legacy(query_emb: List[float], top_k: int = 5):
    """Legacy function: search using old document_chunks schema."""
    init_schema()
    vec_str = "[" + ",".join(f"{x:.6f}" for x in query_emb) + "]"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT content
            FROM document_chunks
            ORDER BY embedding <-> %s::vector
            LIMIT %s
            """,
            (vec_str, top_k),
        )
        return [row[0] for row in cur.fetchall()]

def insert_query(
    question: str,
    answer: str,
    lecture_id: Optional[int] = None,
    course_id: Optional[int] = None,
    user_id: Optional[int] = None,
):
    """Store a question and its answer in the query_history table."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO query_history (lecture_id, course_id, question, answer, user_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (lecture_id, course_id, question, answer, user_id),
        )
        conn.commit()

def get_lecture(lecture_id: int):
    """Get lecture by ID."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, original_name, file_path, page_count, status, created_at, course_id, file_type, transcript, created_by
            FROM lectures
            WHERE id = %s
            """,
            (lecture_id,),
        )
        return cur.fetchone()

def list_lectures(course_id: Optional[int] = None):
    """List lectures, optionally filtered by course."""
    with get_conn() as conn, conn.cursor() as cur:
        base_query = """
            SELECT id, original_name, file_path, page_count, status, created_at, course_id, file_type,
                   COALESCE(transcript IS NOT NULL, FALSE) AS has_transcript
            FROM lectures
        """
        params: List[Any] = []
        if course_id is not None:
            base_query += " WHERE course_id = %s"
            params.append(course_id)

        base_query += " ORDER BY created_at DESC"
        cur.execute(base_query, tuple(params))
        return cur.fetchall()

def delete_lecture(lecture_id: int):
    """Delete a lecture and all its chunks (CASCADE)."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM lectures WHERE id = %s", (lecture_id,))
        conn.commit()

def get_query_history(limit: int = 10):
    """Retrieve recent query history."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, question, answer, created_at
            FROM query_history
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()


def create_user(email: str, password_hash: str, role: str = "student") -> int:
    """Create a new user."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO users (email, password_hash, role)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (email, password_hash, role),
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            raise ValueError(f"User with email {email} already exists")


def get_user_by_email(email: str):
    """Get user by email."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, email, password_hash, role, created_at
            FROM users
            WHERE email = %s
            """,
            (email,),
        )
        return cur.fetchone()


def get_user_by_id(user_id: int):
    """Get user by ID."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, email, password_hash, role, created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        return cur.fetchone()


def add_user_to_course(user_id: int, course_id: int):
    """Add a user to a course (many-to-many relationship)."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO user_courses (user_id, course_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, course_id) DO NOTHING
                """,
                (user_id, course_id),
            )
            conn.commit()
        except psycopg.errors.IntegrityError:
            conn.rollback()
            raise ValueError("User-course relationship already exists")


def get_user_courses(user_id: int) -> List[int]:
    """Get list of course IDs for a user."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT course_id
            FROM user_courses
            WHERE user_id = %s
            """,
            (user_id,),
        )
        return [row[0] for row in cur.fetchall()]


def can_user_access_course(user_id: int, course_id: int, user_role: str) -> bool:
    """
    Check if a user can access a course.
    - Admins can access all courses
    - Instructors can access courses they're assigned to (via course_instructors) or all if no assignments
    - Students can only access courses they're enrolled in
    """
    if user_role == "admin":
        return True
    
    if user_role == "instructor":
        # Check if instructor is assigned to this course
        init_schema()
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM course_instructors
                WHERE course_id = %s AND instructor_id = %s
                """,
                (course_id, user_id),
            )
            is_assigned = cur.fetchone()[0] > 0
            
            # If there are any course-instructor assignments, only show assigned courses
            # Otherwise, show all courses (backward compatibility)
            cur.execute("SELECT COUNT(*) FROM course_instructors")
            has_assignments = cur.fetchone()[0] > 0
            
            if has_assignments:
                return is_assigned
            else:
                # No assignments exist yet, show all courses (backward compatibility)
                return True
    
    # Students can only access courses they're enrolled in
    user_courses = get_user_courses(user_id)
    return course_id in user_courses


def can_user_access_lecture(user_id: int, lecture_id: int, user_role: str) -> bool:
    """
    Check if a user can access a lecture.
    - Admins and instructors can access all lectures
    - Students can only access lectures in courses they're enrolled in
    """
    if user_role in ("admin", "instructor"):
        return True
    
    lecture = get_lecture(lecture_id)
    if not lecture:
        return False
    
    course_id = lecture[6]  # course_id is at index 6
    if course_id is None:
        return False
    
    return can_user_access_course(user_id, course_id, user_role)