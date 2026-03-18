import psycopg.errors
from typing import Any, Dict, List

from .connection import get_conn
from .schema import init_schema


def add_user_to_course(user_id: int, course_id: int, role: str = "student") -> None:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_courses (user_id, course_id, role)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, course_id) DO NOTHING
            """,
            (user_id, course_id, role),
        )
        conn.commit()


def create_user(email: str, password_hash: str, role: str = "student") -> int:
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


def get_user_courses(user_id: int) -> List[int]:
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


def get_user_courses_with_details(user_id: int) -> List[Dict[str, Any]]:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
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
                "join_code": r[4],
                "lecture_count": r[5],
            }
            for r in rows
        ]
