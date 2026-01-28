# src/db.py
import json
import psycopg
import psycopg.errors
from typing import List, Tuple, Optional, Any, Dict
from .config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS, PG_DIM
import random
import string
from datetime import datetime

FILE_TYPES = ("pdf", "audio", "slides")

DEFAULT_COURSE_NAME = "General Course"
DEFAULT_COURSE_DESCRIPTION = "Default course for uncategorized lectures"

def generate_join_code(length=6):
    """Generates a random uppercase alphanumeric code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
def add_user_to_course(
    user_id: int,
    course_id: int,
    role: str = 'student',
    section_id: Optional[int] = None,
    group_id: Optional[int] = None,
) -> None:
    """Links a user to a course. Used by auth and instructor tools."""
    init_schema()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_courses (user_id, course_id, role, section_id, group_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, course_id) DO NOTHING
                """,
                (user_id, course_id, role, section_id, group_id)
            )
            conn.commit()

def enroll_student_by_code(user_id: int, join_code: str) -> int:
    """Links a student to a course using the unique join code."""
    init_schema()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM courses WHERE UPPER(join_code) = %s", 
                (join_code.strip().upper(),)
            )
            course = cur.fetchone()
            if not course:
                raise ValueError("Invalid join code.")
            course_id = course[0]
            # Ensure student has a section assignment
            section_id = get_or_create_default_section(course_id)
            add_user_to_course(user_id, course_id, 'student', section_id=section_id)
            return course_id
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
                join_code TEXT UNIQUE, -- Add this line
                term_year INT,
                term_number INT,
                duration_minutes INT,
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
                section_id INT,
                group_id INT,
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

        # Add section/group columns if they don't exist (migration)
        cur.execute("""
            ALTER TABLE user_courses
            ADD COLUMN IF NOT EXISTS section_id INT;
        """)
        cur.execute("""
            ALTER TABLE user_courses
            ADD COLUMN IF NOT EXISTS group_id INT;
        """)

        # Sections table (per course)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS course_sections (
                id SERIAL PRIMARY KEY,
                course_id INT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(course_id, name)
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS course_sections_course_id_idx
            ON course_sections(course_id);
        """)

        # Groups table (per section)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS section_groups (
                id SERIAL PRIMARY KEY,
                section_id INT NOT NULL REFERENCES course_sections(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(section_id, name)
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS section_groups_section_id_idx
            ON section_groups(section_id);
        """)

        # Announcements table (per course)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS course_announcements (
                id SERIAL PRIMARY KEY,
                course_id INT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                message TEXT NOT NULL,
                created_by INT REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS course_announcements_course_id_idx
            ON course_announcements(course_id);
        """)

        # Upload requests table (student -> instructor approval)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lecture_upload_requests (
                id SERIAL PRIMARY KEY,
                course_id INT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                student_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                original_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_by INT REFERENCES users(id) ON DELETE SET NULL,
                reviewed_at TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS lecture_upload_requests_course_idx
            ON lecture_upload_requests(course_id);
        """)
        
        # Create course_instructors table for instructor assignments
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
        # --- ADD THE NEW JOIN CODE MIGRATION HERE ---
        cur.execute("""
            ALTER TABLE courses
            ADD COLUMN IF NOT EXISTS join_code TEXT UNIQUE;
        """)
        cur.execute("""
            ALTER TABLE courses
            ADD COLUMN IF NOT EXISTS term_year INT;
        """)
        cur.execute("""
            ALTER TABLE courses
            ADD COLUMN IF NOT EXISTS term_number INT;
        """)
        cur.execute("""
            ALTER TABLE courses
            ADD COLUMN IF NOT EXISTS duration_minutes INT;
        """)

        # Backfill term_year/term_number for existing courses
        cur.execute("""
            UPDATE courses
            SET term_year = EXTRACT(YEAR FROM created_at)::INT,
                term_number = CASE WHEN EXTRACT(MONTH FROM created_at) < 7 THEN 1 ELSE 2 END
            WHERE term_year IS NULL OR term_number IS NULL;
        """)
        cur.execute("""
            UPDATE courses
            SET duration_minutes = 90
            WHERE duration_minutes IS NULL;
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

        # Flashcard sets table (stores generation runs)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS flashcard_sets (
                id SERIAL PRIMARY KEY,
                lecture_id INT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
                created_by_user_id INT REFERENCES users(id) ON DELETE SET NULL,
                strategy TEXT NOT NULL DEFAULT 'keypoints_v1',
                seed INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS flashcard_sets_lecture_id_idx
            ON flashcard_sets (lecture_id);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS flashcard_sets_created_at_idx
            ON flashcard_sets (created_at DESC);
        """)
        
        # Flashcards table for study materials (updated schema)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS flashcards (
                id SERIAL PRIMARY KEY,
                flashcard_set_id INT REFERENCES flashcard_sets(id) ON DELETE CASCADE,
                lecture_id INT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source_keypoint_id INT,
                source_chunk_ids JSONB,
                quality_score FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS flashcards_lecture_id_idx
            ON flashcards (lecture_id);
        """)
        
        # Only create flashcard_set_id index if column exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'flashcards' 
                AND column_name = 'flashcard_set_id'
            );
        """)
        has_flashcard_set_id = cur.fetchone()[0]
        if has_flashcard_set_id:
            cur.execute("""
                CREATE INDEX IF NOT EXISTS flashcards_flashcard_set_id_idx
                ON flashcards (flashcard_set_id);
            """)
        
        # Migrate existing flashcards to new schema if needed
        # Check if old columns exist and migrate
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'flashcards' 
                AND column_name = 'front'
            );
        """)
        has_old_schema = cur.fetchone()[0]
        
        # Check if new columns exist
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'flashcards' 
            AND column_name IN ('question', 'flashcard_set_id')
        """)
        existing_cols = {row[0] for row in cur.fetchall()}
        has_new_schema = 'question' in existing_cols and 'flashcard_set_id' in existing_cols
        
        # Only migrate if old schema exists and new schema doesn't
        if has_old_schema and not has_new_schema:
            # Add new columns first (without foreign key constraint initially)
            try:
                cur.execute("""
                    ALTER TABLE flashcards 
                    ADD COLUMN IF NOT EXISTS question TEXT,
                    ADD COLUMN IF NOT EXISTS answer TEXT,
                    ADD COLUMN IF NOT EXISTS flashcard_set_id INT,
                    ADD COLUMN IF NOT EXISTS source_keypoint_id INT,
                    ADD COLUMN IF NOT EXISTS source_chunk_ids JSONB,
                    ADD COLUMN IF NOT EXISTS quality_score FLOAT,
                    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                """)
            except Exception as e:
                print(f"[WARN] Error adding new columns: {e}")
            
            # Create default sets for existing flashcards first (before FK constraint)
            try:
                cur.execute("""
                    INSERT INTO flashcard_sets (lecture_id, strategy)
                    SELECT DISTINCT lecture_id, 'migrated_v1'
                    FROM flashcards
                    WHERE lecture_id NOT IN (
                        SELECT DISTINCT lecture_id FROM flashcard_sets
                    )
                    RETURNING id, lecture_id;
                """)
                migrated_sets = cur.fetchall()
                set_map = {lecture_id: set_id for set_id, lecture_id in migrated_sets}
            except Exception as e:
                print(f"[WARN] Error creating flashcard sets: {e}")
                set_map = {}
            
            # Migrate data from old columns to new columns
            try:
                cur.execute("""
                    SELECT id, lecture_id, front, back 
                    FROM flashcards
                    WHERE (question IS NULL OR answer IS NULL) AND front IS NOT NULL
                """)
                for card_id, lecture_id, front, back in cur.fetchall():
                    set_id = set_map.get(lecture_id)
                    if set_id and front and back:
                        try:
                            cur.execute("""
                                UPDATE flashcards 
                                SET question = %s, answer = %s, flashcard_set_id = %s
                                WHERE id = %s
                            """, (front, back, set_id, card_id))
                        except Exception as e:
                            print(f"[WARN] Error migrating flashcard {card_id}: {e}")
            except Exception as e:
                print(f"[WARN] Error during data migration: {e}")
            
            # Add foreign key constraint after data is migrated
            try:
                cur.execute("""
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.table_constraints 
                            WHERE constraint_name = 'flashcards_flashcard_set_id_fkey'
                            AND table_name = 'flashcards'
                        ) THEN
                            ALTER TABLE flashcards 
                            ADD CONSTRAINT flashcards_flashcard_set_id_fkey 
                            FOREIGN KEY (flashcard_set_id) REFERENCES flashcard_sets(id) ON DELETE CASCADE;
                        END IF;
                    END $$;
                """)
            except Exception as e:
                print(f"[WARN] Note: Foreign key constraint may already exist or failed: {e}")
            
            print("[INFO] Attempted migration of flashcards to new schema")
        
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
        INSERT INTO courses (name, description, term_year, term_number, duration_minutes)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            DEFAULT_COURSE_NAME,
            DEFAULT_COURSE_DESCRIPTION,
            datetime.utcnow().year,
            1 if datetime.utcnow().month < 7 else 2,
            90,
        ),
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


def create_course(
    name: str,
    description: Optional[str] = None,
    created_by: Optional[int] = None,
    term_year: Optional[int] = None,
    term_number: Optional[int] = None,
    duration_minutes: Optional[int] = None,
) -> int:
    """Create a new course with a unique randomized join code."""
    init_schema()
    join_code = generate_join_code()
    
    with get_conn() as conn, conn.cursor() as cur:
        if term_year is None or term_number is None:
            now = datetime.utcnow()
            term_year = term_year or now.year
            term_number = term_number or (1 if now.month < 7 else 2)
        cur.execute(
            """
            INSERT INTO courses (name, description, created_by, join_code, term_year, term_number, duration_minutes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (name, description, created_by, join_code, term_year, term_number, duration_minutes),
        )
        course_id = cur.fetchone()[0]
        conn.commit()
        return course_id


def list_courses():
    """List all courses with their join codes."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, description, created_at, join_code, term_year, term_number, duration_minutes
            FROM courses
            ORDER BY created_at DESC
            """
        )
        return cur.fetchall()

def get_course(course_id: int):
    """Get a single course including the join code."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, description, created_at, join_code, term_year, term_number, duration_minutes
            FROM courses
            WHERE id = %s
            """,
            (course_id,),
        )
        return cur.fetchone()

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
    """Return stored flashcards for a lecture (legacy compatibility - returns latest set)."""
    with get_conn() as conn, conn.cursor() as cur:
        # Try new schema first
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'flashcards' 
            AND column_name = 'question'
        """)
        has_new_schema = bool(cur.fetchone())
        
        if has_new_schema:
            cur.execute(
                """
                SELECT f.id, f.question, f.answer, NULL as page_number
                FROM flashcards f
                WHERE f.lecture_id = %s
                ORDER BY f.created_at DESC
                LIMIT 100
                """,
                (lecture_id,),
            )
        else:
            # Old schema fallback
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
    """Replace all flashcards for a lecture (legacy function - creates a new set)."""
    with get_conn() as conn, conn.cursor() as cur:
        # Create a new set
        cur.execute("""
            INSERT INTO flashcard_sets (lecture_id, strategy)
            VALUES (%s, 'legacy_v1')
            RETURNING id
        """, (lecture_id,))
        set_row = cur.fetchone()
        set_id = set_row[0] if set_row else None
        
        # Delete old flashcards for this lecture (if using old schema)
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'flashcards' AND column_name = 'front'")
        has_old = bool(cur.fetchone())
        
        if has_old:
            cur.execute("DELETE FROM flashcards WHERE lecture_id = %s", (lecture_id,))
            for front, back, page in cards:
                cur.execute(
                    """
                    INSERT INTO flashcards (lecture_id, front, back, page_number)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (lecture_id, front, back, page),
                )
        else:
            # New schema
            cur.execute("DELETE FROM flashcards WHERE lecture_id = %s", (lecture_id,))
            for front, back, _ in cards:
                cur.execute(
                    """
                    INSERT INTO flashcards (lecture_id, flashcard_set_id, question, answer)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (lecture_id, set_id, front, back),
                )
        conn.commit()


def create_flashcard_set(
    lecture_id: int,
    strategy: str = "keypoints_v1",
    created_by_user_id: Optional[int] = None,
    seed: Optional[int] = None,
) -> int:
    """Create a new flashcard set and return its ID."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO flashcard_sets (lecture_id, created_by_user_id, strategy, seed)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (lecture_id, created_by_user_id, strategy, seed),
        )
        set_id = cur.fetchone()[0]
        conn.commit()
        return set_id


def insert_flashcards(
    flashcard_set_id: int,
    lecture_id: int,
    flashcards: List[Dict[str, Any]],
):
    """Insert flashcards for a set."""
    with get_conn() as conn, conn.cursor() as cur:
        for card in flashcards:
            cur.execute(
                """
                INSERT INTO flashcards (
                    flashcard_set_id, lecture_id, question, answer,
                    source_keypoint_id, source_chunk_ids, quality_score
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    flashcard_set_id,
                    lecture_id,
                    card.get("question"),
                    card.get("answer"),
                    card.get("source_keypoint_id"),
                    json.dumps(card.get("source_chunk_ids")) if card.get("source_chunk_ids") else None,
                    card.get("quality_score"),
                ),
            )
        conn.commit()


def get_latest_flashcard_set(lecture_id: int) -> Optional[Tuple[int, str, Optional[int]]]:
    """Get the latest flashcard set for a lecture. Returns (set_id, strategy, created_by_user_id) or None."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, strategy, created_by_user_id
            FROM flashcard_sets
            WHERE lecture_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (lecture_id,))
        row = cur.fetchone()
        return row if row else None


def get_flashcard_set_by_id(set_id: int) -> Optional[Tuple[int, int, str, Optional[int]]]:
    """Get flashcard set by ID. Returns (id, lecture_id, strategy, created_by_user_id) or None."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, lecture_id, strategy, created_by_user_id
            FROM flashcard_sets
            WHERE id = %s
        """, (set_id,))
        return cur.fetchone()


def list_flashcards_by_set(set_id: int) -> List[Tuple[int, str, str, Optional[int], Optional[float]]]:
    """Get flashcards for a specific set. Returns (id, question, answer, source_keypoint_id, quality_score)."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, question, answer, source_keypoint_id, quality_score
            FROM flashcards
            WHERE flashcard_set_id = %s
            ORDER BY quality_score DESC NULLS LAST, id
        """, (set_id,))
        return cur.fetchall()


def get_previous_flashcard_questions(lecture_id: int, limit_sets: int = 3) -> List[str]:
    """Get questions from previous flashcard sets for deduplication."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT f.question
            FROM flashcards f
            JOIN flashcard_sets fs ON f.flashcard_set_id = fs.id
            WHERE fs.lecture_id = %s
            AND fs.id IN (
                SELECT id FROM flashcard_sets
                WHERE lecture_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            )
        """, (lecture_id, lecture_id, limit_sets))
        return [row[0] for row in cur.fetchall()]


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
            SELECT l.id, l.original_name, l.file_path, l.page_count, l.status, l.created_at, l.course_id, l.file_type,
                   l.transcript, l.created_by, u.role
            FROM lectures l
            LEFT JOIN users u ON u.id = l.created_by
            WHERE l.id = %s
            """,
            (lecture_id,),
        )
        return cur.fetchone()

def list_lectures(course_id: Optional[int] = None):
    """List lectures, optionally filtered by course."""
    with get_conn() as conn, conn.cursor() as cur:
        base_query = """
            SELECT l.id, l.original_name, l.file_path, l.page_count, l.status, l.created_at, l.course_id, l.file_type,
                   COALESCE(l.transcript IS NOT NULL, FALSE) AS has_transcript, l.created_by, u.role
            FROM lectures l
            LEFT JOIN users u ON u.id = l.created_by
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


def get_user_courses_with_details(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve all courses a user is enrolled in, including the join_code."""
    init_schema()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.name, c.description, c.created_at, c.join_code,
                       (SELECT COUNT(*) FROM lectures WHERE course_id = c.id) as lecture_count
                FROM courses c
                JOIN user_courses uc ON c.id = uc.course_id
                WHERE uc.user_id = %s
                ORDER BY c.created_at DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "name": r[1],
                    "description": r[2],
                    "created_at": r[3].isoformat() if r[3] else None,
                    "join_code": r[4], # Make sure this is index 4
                    "lecture_count": r[5],
                }
                for r in rows
            ]


def assign_instructor_to_course(course_id: int, instructor_id: int, assigned_by: int):
    """Assign an instructor to a course."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO course_instructors (course_id, instructor_id, assigned_by)
                VALUES (%s, %s, %s)
                ON CONFLICT (course_id, instructor_id) DO NOTHING
                RETURNING assigned_at
                """,
                (course_id, instructor_id, assigned_by),
            )
            result = cur.fetchone()
            conn.commit()
            return result[0] if result else None
        except Exception as e:
            conn.rollback()
            raise ValueError(f"Failed to assign instructor: {str(e)}")


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


def get_or_create_default_section(course_id: int) -> int:
    """Ensure a default section exists for a course and return its ID."""
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM course_sections
            WHERE course_id = %s
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (course_id,),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            """
            INSERT INTO course_sections (course_id, name)
            VALUES (%s, %s)
            RETURNING id
            """,
            (course_id, "Section 1"),
        )
        section_id = cur.fetchone()[0]
        conn.commit()
        return section_id


def can_user_access_course(user_id: int, course_id: int, user_role: str) -> bool:
    """
    Check if a user can access a course.
    - Instructors can access courses they created or are assigned to (via course_instructors) or all if no assignments
    - Students can only access courses they're enrolled in
    """
    if user_role == "instructor":
        init_schema()
        with get_conn() as conn, conn.cursor() as cur:
            # Check if instructor created the course
            cur.execute(
                """
                SELECT created_by FROM courses WHERE id = %s
                """,
                (course_id,),
            )
            course_row = cur.fetchone()
            if course_row and course_row[0] == user_id:
                return True
            
            # Check if instructor is assigned to this course
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
    - Instructors can access all lectures
    - Students can only access lectures in courses they're enrolled in
    """
    if user_role == "instructor":
        return True
    
    lecture = get_lecture(lecture_id)
    if not lecture:
        return False
    
    course_id = lecture[6]  # course_id is at index 6
    if course_id is None:
        return False
    
    return can_user_access_course(user_id, course_id, user_role)

def is_instructor_for_course(user_id: int, course_id: int) -> bool:
    """
    Returns True if user is allowed to manage this course as an instructor.
    Accepts either:
    - user is the course creator (courses.created_by)
    - user is in course_instructors for that course
    """
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        # creator check
        cur.execute("SELECT created_by FROM courses WHERE id = %s", (course_id,))
        row = cur.fetchone()
        if not row:
            return False  # course doesn't exist
        created_by = row[0]
        if created_by is not None and created_by == user_id:
            return True

        # assignment check
        cur.execute(
            """
            SELECT 1
            FROM course_instructors
            WHERE course_id = %s AND instructor_id = %s
            LIMIT 1
            """,
            (course_id, user_id),
        )
        return cur.fetchone() is not None


def delete_course_as_instructor(course_id: int, instructor_id: int) -> None:
    init_schema()
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check ownership
            cur.execute("SELECT id FROM courses WHERE id = %s AND created_by = %s", (course_id, instructor_id))
            if not cur.fetchone():
                raise ValueError("Unauthorized or course not found")

            # MANUALLY delete heavy data first to prevent the "Infinite Load"
            cur.execute("DELETE FROM chunks WHERE lecture_id IN (SELECT id FROM lectures WHERE course_id = %s)", (course_id,))
            cur.execute("DELETE FROM flashcards WHERE lecture_id IN (SELECT id FROM lectures WHERE course_id = %s)", (course_id,))
            cur.execute("DELETE FROM lectures WHERE course_id = %s", (course_id,))
            
            # Now delete the course row
            cur.execute("DELETE FROM user_courses WHERE course_id = %s", (course_id,))
            cur.execute("DELETE FROM courses WHERE id = %s", (course_id,))
            conn.commit()

def enroll_student_by_code(user_id: int, join_code: str) -> int:
    """Links a student to a course using the unique join code."""
    init_schema()
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1. Find the course by the code (case-insensitive)
            cur.execute(
                "SELECT id FROM courses WHERE UPPER(join_code) = %s", 
                (join_code.strip().upper(),)
            )
            course = cur.fetchone()
            
            if not course:
                raise ValueError("Invalid join code. Please check with your instructor.")
            
            course_id = course[0]
            
            # 2. Check if student is already enrolled to avoid duplicates
            cur.execute(
                "SELECT 1 FROM user_courses WHERE user_id = %s AND course_id = %s",
                (user_id, course_id)
            )
            if cur.fetchone():
                return course_id # Already enrolled, just return the ID
            
            # 3. Enroll the student
            cur.execute(
                "INSERT INTO user_courses (user_id, course_id, role) VALUES (%s, %s, 'student')",
                (user_id, course_id)
            )
            conn.commit()
            return course_id