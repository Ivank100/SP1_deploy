"""This file implements analytics logic for instructor insights.
It turns raw lecture or question data into summaries the API can return."""


from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ...db.postgres import get_conn
from .clustering import cluster_questions


def get_query_trends(
    days: int = 30,
    group_by: str = "day",
    course_ids: Optional[List[int]] = None,
    lecture_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    with get_conn() as conn, conn.cursor() as cur:
        cutoff = datetime.now() - timedelta(days=days)

        params = [cutoff]
        base_query = """
            SELECT qh.question, qh.created_at
            FROM query_history qh
            LEFT JOIN lectures l ON qh.lecture_id = l.id
            WHERE qh.created_at >= %s
        """

        if course_ids:
            base_query += " AND (l.course_id = ANY(%s) OR (qh.course_id = ANY(%s) AND qh.lecture_id IS NULL))"
            params.extend([course_ids, course_ids])

        if lecture_id:
            base_query += " AND qh.lecture_id = %s"
            params.append(lecture_id)

        base_query += " ORDER BY qh.created_at DESC"
        cur.execute(base_query, tuple(params))
        rows = cur.fetchall()

    return _group_by_week(rows) if group_by == "week" else _group_by_day(rows)


def _group_by_day(rows: List[Tuple[str, datetime]]) -> List[Dict[str, Any]]:
    by_day: Dict[str, List[str]] = defaultdict(list)
    for question, created_at in rows:
        day_key = created_at.strftime("%Y-%m-%d")
        by_day[day_key].append(question)

    return [
        {"period": day, "count": len(questions), "questions": questions[:5]}
        for day, questions in sorted(by_day.items())
    ]


def _group_by_week(rows: List[Tuple[str, datetime]]) -> List[Dict[str, Any]]:
    by_week: Dict[str, List[str]] = defaultdict(list)
    for question, created_at in rows:
        monday = created_at - timedelta(days=created_at.weekday())
        week_key = monday.strftime("%Y-%m-%d")
        by_week[week_key].append(question)

    return [
        {"period": week, "count": len(questions), "questions": questions[:5]}
        for week, questions in sorted(by_week.items())
    ]


def get_lecture_health_metrics(
    course_ids: Optional[List[int]] = None,
    lecture_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    with get_conn() as conn, conn.cursor() as cur:
        params = []
        base_query = """
            SELECT l.id, l.original_name, COUNT(qh.id) as query_count
            FROM lectures l
            LEFT JOIN query_history qh ON qh.lecture_id = l.id
            WHERE l.status = 'completed'
        """

        if course_ids:
            base_query += " AND l.course_id = ANY(%s)"
            params.append(course_ids)

        if lecture_id:
            base_query += " AND l.id = %s"
            params.append(lecture_id)

        base_query += " GROUP BY l.id, l.original_name ORDER BY query_count DESC"
        cur.execute(base_query, tuple(params) if params else ())
        lecture_stats = cur.fetchall()

        params2 = []
        questions_query = """
            SELECT qh.lecture_id, qh.question
            FROM query_history qh
            WHERE qh.lecture_id IS NOT NULL
        """

        if course_ids:
            questions_query += " AND EXISTS (SELECT 1 FROM lectures l WHERE l.id = qh.lecture_id AND l.course_id = ANY(%s))"
            params2.append(course_ids)

        if lecture_id:
            questions_query += " AND qh.lecture_id = %s"
            params2.append(lecture_id)

        cur.execute(questions_query, tuple(params2) if params2 else ())
        questions_by_lecture: Dict[int, List[str]] = defaultdict(list)
        for lecture_id_value, question in cur.fetchall():
            questions_by_lecture[lecture_id_value].append(question)

    result = []
    for lecture_id_value, lecture_name, query_count in lecture_stats:
        questions = questions_by_lecture.get(lecture_id_value, [])
        avg_complexity = (
            sum(len(question.split()) for question in questions) / len(questions)
            if questions else 0
        )
        clusters = cluster_questions(questions, n_clusters=3) if questions else []

        result.append(
            {
                "lecture_id": lecture_id_value,
                "lecture_name": lecture_name,
                "query_count": query_count,
                "avg_complexity": round(avg_complexity, 1),
                "top_clusters": [
                    {
                        "representative_question": cluster["representative_question"],
                        "count": cluster["count"],
                    }
                    for cluster in clusters[:3]
                ],
            }
        )

    return result


def get_all_queries(
    limit: int = 100,
    lecture_id: Optional[int] = None,
    course_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    with get_conn() as conn, conn.cursor() as cur:
        base_query = """
            SELECT qh.id, qh.question, qh.answer, qh.lecture_id,
                   COALESCE(l.original_name, 'Course-level query') as lecture_name,
                   qh.created_at, qh.user_id, u.email as user_email
            FROM query_history qh
            LEFT JOIN lectures l ON qh.lecture_id = l.id
            LEFT JOIN users u ON qh.user_id = u.id
            WHERE 1=1
        """
        params: List[Any] = []

        if lecture_id:
            base_query += " AND qh.lecture_id = %s"
            params.append(lecture_id)

        if course_id:
            base_query += " AND (l.course_id = %s OR (qh.course_id = %s AND qh.lecture_id IS NULL))"
            params.append(course_id)
            params.append(course_id)

        base_query += " ORDER BY qh.created_at DESC LIMIT %s"
        params.append(limit)

        cur.execute(base_query, tuple(params))
        rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "question": row[1],
            "answer": row[2],
            "lecture_id": row[3],
            "lecture_name": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
            "user_id": row[6],
            "user_email": row[7] if len(row) > 7 else None,
        }
        for row in rows
    ]
