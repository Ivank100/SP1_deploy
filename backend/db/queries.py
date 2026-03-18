from typing import Optional

from .connection import get_conn
from .schema import init_schema


def insert_query(
    question: str,
    answer: str,
    lecture_id: Optional[int] = None,
    course_id: Optional[int] = None,
    user_id: Optional[int] = None,
    page_number: Optional[int] = None,
):
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO query_history (lecture_id, course_id, question, answer, user_id, page_number)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (lecture_id, course_id, question, answer, user_id, page_number),
        )
        conn.commit()


def get_query_history(limit: int = 10):
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
