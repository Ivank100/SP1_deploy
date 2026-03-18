"""This file contains database helpers for queries records.
It wraps SQL reads and writes used by the API and service layers."""


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
