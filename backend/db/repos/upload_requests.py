from typing import List

from ..connection import get_conn
from ..schema import init_schema


def get_upload_request(request_id: int):
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, course_id, student_id, original_name, file_path, file_type, status,
                   created_at, reviewed_by, reviewed_at
            FROM lecture_upload_requests
            WHERE id = %s
            """,
            (request_id,),
        )
        return cur.fetchone()


def delete_upload_request(request_id: int) -> None:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM lecture_upload_requests WHERE id = %s", (request_id,))
        conn.commit()


def list_upload_request_file_paths(course_id: int) -> List[str]:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT file_path
            FROM lecture_upload_requests
            WHERE course_id = %s
            """,
            (course_id,),
        )
        return [row[0] for row in cur.fetchall() if row[0]]
