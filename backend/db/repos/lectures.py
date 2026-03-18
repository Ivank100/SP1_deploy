import json
from typing import Any, Dict, List, Optional

from ..connection import FILE_TYPES, get_conn
from ..schema import _get_or_create_default_course, init_schema
from .courses import can_user_access_course


def insert_lecture(
    original_name: str,
    file_path: str,
    page_count: int = 0,
    status: str = "processing",
    course_id: Optional[int] = None,
    file_type: str = "pdf",
    created_by: Optional[int] = None,
) -> int:
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
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE lectures SET status = %s WHERE id = %s", (status, lecture_id))
        conn.commit()


def update_lecture_name(lecture_id: int, name: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE lectures SET original_name = %s WHERE id = %s", (name, lecture_id))
        conn.commit()


def update_lecture_file(lecture_id: int, original_name: str, file_path: str, page_count: int, file_type: str = "pdf"):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE lectures
            SET original_name = %s, file_path = %s, page_count = %s, file_type = %s, status = 'processing'
            WHERE id = %s
            """,
            (original_name, file_path, page_count, file_type, lecture_id),
        )
        conn.commit()


def reset_lecture_materials(lecture_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE lectures SET summary = NULL, key_points = NULL, transcript = NULL WHERE id = %s",
            (lecture_id,),
        )
        conn.commit()


def list_lecture_resources(lecture_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, lecture_id, title, url, created_at
            FROM lecture_resources
            WHERE lecture_id = %s
            ORDER BY created_at DESC
            """,
            (lecture_id,),
        )
        return cur.fetchall()


def add_lecture_resource(lecture_id: int, title: str, url: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO lecture_resources (lecture_id, title, url)
            VALUES (%s, %s, %s)
            RETURNING id, lecture_id, title, url, created_at
            """,
            (lecture_id, title, url),
        )
        resource = cur.fetchone()
        conn.commit()
        return resource


def delete_lecture_resource(resource_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM lecture_resources WHERE id = %s", (resource_id,))
        conn.commit()


def save_lecture_summary(lecture_id: int, summary: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE lectures SET summary = %s WHERE id = %s", (summary, lecture_id))
        conn.commit()


def save_lecture_transcript(lecture_id: int, transcript: Dict[str, Any]):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE lectures SET transcript = %s WHERE id = %s", (json.dumps(transcript), lecture_id))
        conn.commit()


def get_lecture_transcript(lecture_id: int) -> Optional[Dict[str, Any]]:
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
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE lectures SET key_points = %s WHERE id = %s", (json.dumps(key_points), lecture_id))
        conn.commit()


def get_lecture_study_materials(lecture_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT summary, key_points FROM lectures WHERE id = %s", (lecture_id,))
        row = cur.fetchone()
        if not row:
            return None
        summary, key_points_raw = row
        try:
            key_points = json.loads(key_points_raw) if key_points_raw else []
        except json.JSONDecodeError:
            key_points = []
        return {"summary": summary, "key_points": key_points}


def get_lecture(lecture_id: int):
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
    with get_conn() as conn, conn.cursor() as cur:
        base_query = """
            SELECT l.id, l.original_name, l.file_path, l.page_count, l.status, l.created_at, l.course_id, l.file_type,
                   COALESCE(l.transcript IS NOT NULL, FALSE) AS has_transcript, l.created_by, u.role
            FROM lectures l
            LEFT JOIN users u ON u.id = l.created_by
            WHERE l.status != 'archived'
        """
        params: List[Any] = []
        if course_id is not None:
            base_query += " AND course_id = %s"
            params.append(course_id)
        base_query += " ORDER BY created_at DESC"
        cur.execute(base_query, tuple(params))
        return cur.fetchall()


def delete_lecture(lecture_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM lectures WHERE id = %s", (lecture_id,))
        conn.commit()


def can_user_access_lecture(user_id: int, lecture_id: int, user_role: str) -> bool:
    if user_role == "instructor":
        return True
    lecture = get_lecture(lecture_id)
    if not lecture:
        return False
    course_id = lecture[6]
    if course_id is None:
        return False
    return can_user_access_course(user_id, course_id, user_role)
