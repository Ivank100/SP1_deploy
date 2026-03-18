"""This file defines course analytics endpoints for instructors and staff.
It returns summaries built from course-level question patterns and engagement data."""


import csv
from datetime import datetime, timedelta
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from ....db.postgres import get_conn
from ....services.analytics import cluster_questions, get_all_queries
from ...dependencies.auth import get_current_instructor
from ...schemas import CourseAnalyticsResponse
from .shared import ensure_course_access

router = APIRouter()


@router.get("/{course_id}/analytics", response_model=CourseAnalyticsResponse)
async def get_course_analytics(course_id: int, current_user: dict = Depends(get_current_instructor)):
    ensure_course_access(course_id, current_user)
    queries = get_all_queries(limit=1000, course_id=course_id)
    total_questions = len(queries)
    active_students = len(set(q["user_id"] for q in queries if q.get("user_id")))
    questions = [q["question"] for q in queries if q.get("question")]
    clusters = cluster_questions(questions, n_clusters=5) if questions else []
    top_confused_topics = [
        {"topic": c["representative_question"], "count": c["count"], "questions": c.get("questions", [])[:3]}
        for c in clusters[:5]
    ]

    with get_conn() as conn, conn.cursor() as cur:
        now = datetime.now()
        last_7_days = now - timedelta(days=7)
        previous_7_days = last_7_days - timedelta(days=7)
        cur.execute(
            """
            SELECT COUNT(*) FROM query_history qh
            LEFT JOIN lectures l ON qh.lecture_id = l.id
            WHERE (l.course_id = %s OR (qh.course_id = %s AND qh.lecture_id IS NULL))
            AND qh.created_at >= %s
            """,
            (course_id, course_id, last_7_days),
        )
        recent_count = cur.fetchone()[0]
        cur.execute(
            """
            SELECT COUNT(*) FROM query_history qh
            LEFT JOIN lectures l ON qh.lecture_id = l.id
            WHERE (l.course_id = %s OR (qh.course_id = %s AND qh.lecture_id IS NULL))
            AND qh.created_at >= %s AND qh.created_at < %s
            """,
            (course_id, course_id, previous_7_days, last_7_days),
        )
        previous_count = cur.fetchone()[0]

    if previous_count > 0:
        trend_percentage = ((recent_count - previous_count) / previous_count) * 100
        trend_direction = "up" if recent_count > previous_count else "down"
    elif recent_count > 0:
        trend_percentage = 100.0
        trend_direction = "up"
    else:
        trend_percentage = 0.0
        trend_direction = "stable"

    return CourseAnalyticsResponse(
        total_questions=total_questions,
        active_students=active_students,
        top_confused_topics=top_confused_topics,
        trend_percentage=round(abs(trend_percentage), 1),
        trend_direction=trend_direction,
    )


@router.get("/{course_id}/questions/export", status_code=status.HTTP_200_OK)
async def export_questions_csv(course_id: int, current_user: dict = Depends(get_current_instructor)):
    ensure_course_access(course_id, current_user)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT qh.id, qh.question, qh.answer, qh.created_at, u.email, l.original_name
            FROM query_history qh
            LEFT JOIN users u ON u.id = qh.user_id
            LEFT JOIN lectures l ON l.id = qh.lecture_id
            WHERE (l.course_id = %s OR (qh.course_id = %s AND qh.lecture_id IS NULL))
            ORDER BY qh.created_at DESC
            """,
            (course_id, course_id),
        )
        rows = cur.fetchall()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "question", "answer", "created_at", "student_email", "lecture_name"])
    for row in rows:
        writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5]])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=course_{course_id}_questions.csv"},
    )
