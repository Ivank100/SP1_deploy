from datetime import datetime
from typing import Any, Dict, List, Optional

from ..connection import generate_join_code, get_conn
from ..schema import init_schema
from .users import get_user_courses


def create_course(
    name: str,
    description: Optional[str] = None,
    created_by: Optional[int] = None,
    term_year: Optional[int] = None,
    term_number: Optional[int] = None,
    duration_minutes: Optional[int] = None,
) -> int:
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


def assign_instructor_to_course(course_id: int, instructor_id: int, assigned_by: int):
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


def get_instructor_assigned_course_ids(instructor_id: int) -> Optional[List[int]]:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM course_instructors")
        has_assignments = cur.fetchone()[0] > 0
        if not has_assignments:
            return None
        cur.execute(
            """
            SELECT course_id
            FROM course_instructors
            WHERE instructor_id = %s
            """,
            (instructor_id,),
        )
        return [row[0] for row in cur.fetchall()]


def get_instructor_visible_course_ids(instructor_id: int) -> Optional[List[int]]:
    assigned_course_ids = get_instructor_assigned_course_ids(instructor_id)
    if assigned_course_ids is None:
        return None

    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id
            FROM courses
            WHERE created_by = %s
            """,
            (instructor_id,),
        )
        created_course_ids = [row[0] for row in cur.fetchall()]
    return list(set(assigned_course_ids + created_course_ids))


def can_user_access_course(user_id: int, course_id: int, user_role: str) -> bool:
    if user_role == "instructor":
        visible_course_ids = get_instructor_visible_course_ids(user_id)
        if visible_course_ids is None:
            return True
        return course_id in visible_course_ids
    return course_id in get_user_courses(user_id)


def is_instructor_for_course(user_id: int, course_id: int) -> bool:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT created_by FROM courses WHERE id = %s", (course_id,))
        row = cur.fetchone()
        if not row:
            return False
        if row[0] is not None and row[0] == user_id:
            return True
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


def get_course_instructors(course_id: int) -> List[Dict[str, Any]]:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT ci.instructor_id, u.email, ci.assigned_at, ci.assigned_by
            FROM course_instructors ci
            JOIN users u ON ci.instructor_id = u.id
            WHERE ci.course_id = %s
            ORDER BY ci.assigned_at DESC
            """,
            (course_id,),
        )
        return [
            {
                "instructor_id": row[0],
                "instructor_email": row[1],
                "assigned_at": row[2].isoformat() if row[2] else None,
                "assigned_by": row[3],
            }
            for row in cur.fetchall()
        ]


def remove_instructor_assignment(course_id: int, instructor_id: int) -> bool:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM course_instructors
            WHERE course_id = %s AND instructor_id = %s
            """,
            (course_id, instructor_id),
        )
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted


def delete_course_as_instructor(course_id: int, instructor_id: int) -> None:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM courses WHERE id = %s AND created_by = %s", (course_id, instructor_id))
        if not cur.fetchone():
            raise ValueError("Unauthorized or course not found")
        cur.execute("DELETE FROM chunks WHERE lecture_id IN (SELECT id FROM lectures WHERE course_id = %s)", (course_id,))
        cur.execute("DELETE FROM flashcards WHERE lecture_id IN (SELECT id FROM lectures WHERE course_id = %s)", (course_id,))
        cur.execute("DELETE FROM lectures WHERE course_id = %s", (course_id,))
        cur.execute("DELETE FROM user_courses WHERE course_id = %s", (course_id,))
        cur.execute("DELETE FROM courses WHERE id = %s", (course_id,))
        conn.commit()


def enroll_student_by_code(user_id: int, join_code: str) -> int:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM courses WHERE UPPER(join_code) = %s", (join_code.strip().upper(),))
        course = cur.fetchone()
        if not course:
            raise ValueError("Invalid join code. Please check with your instructor.")
        course_id = course[0]
        cur.execute(
            "SELECT 1 FROM user_courses WHERE user_id = %s AND course_id = %s",
            (user_id, course_id),
        )
        if cur.fetchone():
            return course_id
        cur.execute(
            """
            INSERT INTO user_courses (user_id, course_id, role)
            VALUES (%s, %s, 'student')
            ON CONFLICT (user_id, course_id) DO NOTHING
            """,
            (user_id, course_id),
        )
        conn.commit()
        return course_id
