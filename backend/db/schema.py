import psycopg.errors
from datetime import datetime
from threading import Lock

from ..core.config import PG_DIM
from .connection import DEFAULT_COURSE_DESCRIPTION, DEFAULT_COURSE_NAME, get_conn

_schema_init_lock = Lock()
_schema_initialized = False


def init_schema():
    """Initialize the database schema and apply lightweight migrations."""
    global _schema_initialized

    if _schema_initialized:
        return

    with _schema_init_lock:
        if _schema_initialized:
            return

        with get_conn() as conn, conn.cursor() as cur:
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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'student',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS users_email_idx ON users(email);")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    join_code TEXT UNIQUE,
                    term_year INT,
                    term_number INT,
                    duration_minutes INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INT REFERENCES users(id) ON DELETE SET NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_courses (
                    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    course_id INT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                    role TEXT DEFAULT 'student',
                    PRIMARY KEY (user_id, course_id)
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS user_courses_user_id_idx ON user_courses(user_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS user_courses_course_id_idx ON user_courses(course_id);")
            cur.execute("""
                ALTER TABLE user_courses
                ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'student';
            """)

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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS course_instructors (
                    course_id INT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                    instructor_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    assigned_by INT REFERENCES users(id) ON DELETE SET NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (course_id, instructor_id)
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS course_instructors_course_id_idx ON course_instructors(course_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS course_instructors_instructor_id_idx ON course_instructors(instructor_id);")

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
            cur.execute("""
                ALTER TABLE lectures
                ADD COLUMN IF NOT EXISTS created_by INT REFERENCES users(id) ON DELETE SET NULL;
            """)
            cur.execute("""
                ALTER TABLE courses
                ADD COLUMN IF NOT EXISTS created_by INT REFERENCES users(id) ON DELETE SET NULL;
            """)
            cur.execute("""ALTER TABLE courses ADD COLUMN IF NOT EXISTS join_code TEXT UNIQUE;""")
            cur.execute("""ALTER TABLE courses ADD COLUMN IF NOT EXISTS term_year INT;""")
            cur.execute("""ALTER TABLE courses ADD COLUMN IF NOT EXISTS term_number INT;""")
            cur.execute("""ALTER TABLE courses ADD COLUMN IF NOT EXISTS duration_minutes INT;""")
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
            cur.execute("""ALTER TABLE lectures ADD COLUMN IF NOT EXISTS summary TEXT;""")
            cur.execute("""ALTER TABLE lectures ADD COLUMN IF NOT EXISTS key_points TEXT;""")
            cur.execute("""ALTER TABLE lectures ADD COLUMN IF NOT EXISTS file_type TEXT;""")
            cur.execute("""ALTER TABLE lectures ALTER COLUMN file_type SET DEFAULT 'pdf';""")
            cur.execute("""UPDATE lectures SET file_type = 'pdf' WHERE file_type IS NULL;""")
            cur.execute("""ALTER TABLE lectures ADD COLUMN IF NOT EXISTS transcript JSONB;""")

            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'lectures' AND column_name = 'course_id'
                );
            """)
            has_course_id = cur.fetchone()[0]
            if not has_course_id:
                cur.execute("""
                    ALTER TABLE lectures
                    ADD COLUMN course_id INT REFERENCES courses(id) ON DELETE CASCADE;
                """)
                print("[INFO] Added course_id column to lectures table")

            cur.execute("SELECT COUNT(*) FROM lectures WHERE course_id IS NULL;")
            missing_course_refs = cur.fetchone()[0]
            if missing_course_refs:
                default_course_id = _get_or_create_default_course(cur)
                cur.execute("UPDATE lectures SET course_id = %s WHERE course_id IS NULL;", (default_course_id,))
                print(f"[INFO] Linked {missing_course_refs} lecture(s) to default course")

            cur.execute("CREATE INDEX IF NOT EXISTS lectures_course_id_idx ON lectures (course_id);")

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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS lecture_resources (
                    id SERIAL PRIMARY KEY,
                    lecture_id INT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS lecture_resources_lecture_id_idx
                ON lecture_resources (lecture_id);
            """)

            cur.execute("""
                DO $$
                BEGIN
                    ALTER TABLE chunks DROP CONSTRAINT IF EXISTS chunks_lecture_id_page_number_chunk_index_key;
                EXCEPTION
                    WHEN undefined_object THEN NULL;
                END$$;
            """)
            cur.execute("""ALTER TABLE chunks ADD COLUMN IF NOT EXISTS timestamp_start DOUBLE PRECISION;""")
            cur.execute("""ALTER TABLE chunks ADD COLUMN IF NOT EXISTS timestamp_end DOUBLE PRECISION;""")
            cur.execute("""
                DO $$
                BEGIN
                    ALTER TABLE chunks ALTER COLUMN page_number DROP NOT NULL;
                EXCEPTION
                    WHEN OTHERS THEN NULL;
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
            cur.execute("""
                CREATE INDEX IF NOT EXISTS chunks_embedding_idx
                ON chunks
                USING ivfflat (embedding vector_cosine_ops);
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS chunks_lecture_id_idx ON chunks (lecture_id);")

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
            cur.execute("CREATE INDEX IF NOT EXISTS flashcard_sets_lecture_id_idx ON flashcard_sets (lecture_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS flashcard_sets_created_at_idx ON flashcard_sets (created_at DESC);")

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
            cur.execute("CREATE INDEX IF NOT EXISTS flashcards_lecture_id_idx ON flashcards (lecture_id);")

            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'flashcards' AND column_name = 'flashcard_set_id'
                );
            """)
            if cur.fetchone()[0]:
                cur.execute("CREATE INDEX IF NOT EXISTS flashcards_flashcard_set_id_idx ON flashcards (flashcard_set_id);")

            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'flashcards' AND column_name = 'front'
                );
            """)
            has_old_schema = cur.fetchone()[0]
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'flashcards'
                AND column_name IN ('question', 'flashcard_set_id')
            """)
            existing_cols = {row[0] for row in cur.fetchall()}
            has_new_schema = "question" in existing_cols and "flashcard_set_id" in existing_cols
            if has_old_schema and not has_new_schema:
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
                    set_map = {lecture_id: set_id for set_id, lecture_id in cur.fetchall()}
                except Exception as e:
                    print(f"[WARN] Error creating flashcard sets: {e}")
                    set_map = {}

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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id SERIAL PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'query_history' AND column_name = 'lecture_id'
                );
            """)
            if not cur.fetchone()[0]:
                cur.execute("""
                    ALTER TABLE query_history
                    ADD COLUMN lecture_id INT REFERENCES lectures(id) ON DELETE SET NULL;
                """)
                print("[INFO] Added lecture_id column to query_history table")

            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'query_history' AND column_name = 'course_id'
                );
            """)
            if not cur.fetchone()[0]:
                cur.execute("""
                    ALTER TABLE query_history
                    ADD COLUMN course_id INT REFERENCES courses(id) ON DELETE SET NULL;
                """)
                print("[INFO] Added course_id column to query_history table")

            cur.execute("CREATE INDEX IF NOT EXISTS query_history_created_at_idx ON query_history (created_at DESC);")
            cur.execute("CREATE INDEX IF NOT EXISTS query_history_lecture_id_idx ON query_history (lecture_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS query_history_course_id_idx ON query_history (course_id);")

            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'query_history' AND column_name = 'user_id'
                );
            """)
            if not cur.fetchone()[0]:
                cur.execute("""
                    ALTER TABLE query_history
                    ADD COLUMN user_id INT REFERENCES users(id) ON DELETE SET NULL;
                """)
                print("[INFO] Added user_id column to query_history table")

            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'query_history' AND column_name = 'page_number'
                );
            """)
            if not cur.fetchone()[0]:
                cur.execute("""
                    ALTER TABLE query_history
                    ADD COLUMN page_number INT;
                """)
                print("[INFO] Added page_number column to query_history table")

            cur.execute("CREATE INDEX IF NOT EXISTS query_history_user_id_idx ON query_history (user_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS query_history_page_number_idx ON query_history (page_number);")

            conn.commit()

        _schema_initialized = True
        print(f"[INFO] Database schema initialized (vector dimension: {PG_DIM})")


def _get_or_create_default_course(cur) -> int:
    """Ensure a default course exists and return its ID."""
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

    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO courses (name, description, term_year, term_number, duration_minutes)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            DEFAULT_COURSE_NAME,
            DEFAULT_COURSE_DESCRIPTION,
            now.year,
            1 if now.month < 7 else 2,
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
