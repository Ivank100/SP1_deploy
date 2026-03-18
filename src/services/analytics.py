# src/analytics.py
"""
Analytics utilities for instructor dashboard: clustering, trends, metrics.
"""
from typing import List, Dict, Any, Tuple, Optional
import math
from collections import defaultdict
from datetime import datetime, timedelta
import json

from ..db.postgres import get_conn, get_lecture, list_lectures, get_lecture_transcript

BIN_SIZE_MIN = 15


def _estimate_duration_minutes(lecture_id: int, lecture_row: Optional[Tuple[Any, ...]] = None) -> float:
    lecture = lecture_row or get_lecture(lecture_id)
    if not lecture:
        return 60.0
    page_count = lecture[3] or 0
    file_type = lecture[7] or "pdf"
    course_id = lecture[6]

    duration_minutes: Optional[float] = None
    if course_id:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT duration_minutes
                FROM courses
                WHERE id = %s
                """,
                (course_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                duration_minutes = float(row[0])
    if duration_minutes is None:
        if file_type == "audio":
            transcript = get_lecture_transcript(lecture_id)
            if transcript:
                segments = transcript.get("segments") or []
                max_end = max((seg.get("end") or 0) for seg in segments) if segments else 0
                if max_end:
                    duration_minutes = max_end / 60.0
            if not duration_minutes:
                duration_minutes = 90.0
        elif file_type == "slides":
            duration_minutes = max(10.0, float(page_count) * 1.5)
        else:
            duration_minutes = max(10.0, float(page_count) * 2.0)

    return min(max(duration_minutes, 10.0), 240.0)


def _count_by_minute_bins(
    timestamps: List[datetime],
    bin_size_minutes: int,
    bin_count: int,
) -> List[int]:
    if not timestamps or bin_count <= 0 or bin_size_minutes <= 0:
        return [0 for _ in range(max(bin_count, 0))]
    start_time = timestamps[0]
    counts = [0 for _ in range(bin_count)]
    for ts in timestamps:
        delta = max((ts - start_time).total_seconds(), 0.0)
        delta_minutes = delta / 60.0
        idx = int(delta_minutes // bin_size_minutes)
        if idx >= bin_count:
            idx = bin_count - 1
        counts[idx] += 1
    return counts
from .embeddings import embed_texts


def cluster_questions(
    questions: List[str], n_clusters: int = 5
) -> List[Dict[str, Any]]:
    """
    Cluster questions using K-means on embeddings.
    
    Returns:
        List of cluster dicts with 'cluster_id', 'questions', 'count', 'representative_question'
    """
    if not questions or len(questions) < n_clusters:
        return []

    try:
        from sklearn.cluster import KMeans
        import numpy as np
    except ImportError:
        # Fallback: simple grouping by first word if sklearn not available
        return _simple_cluster_fallback(questions)

    # Embed all questions
    embeddings = embed_texts(questions)
    X = np.array(embeddings)

    # Cluster
    kmeans = KMeans(n_clusters=min(n_clusters, len(questions)), random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    # Group questions by cluster
    clusters: Dict[int, List[str]] = defaultdict(list)
    for idx, label in enumerate(labels):
        clusters[label].append(questions[idx])

    # Build result: find representative question (closest to centroid)
    result = []
    for cluster_id, cluster_questions in clusters.items():
        if not cluster_questions:
            continue
        # Use first question as representative (or could compute centroid distance)
        result.append({
            "cluster_id": cluster_id,
            "count": len(cluster_questions),
            "questions": cluster_questions[:10],  # Limit to 10 examples
            "representative_question": cluster_questions[0],
        })

    return sorted(result, key=lambda x: x["count"], reverse=True)


def _simple_cluster_fallback(questions: List[str]) -> List[Dict[str, Any]]:
    """Fallback clustering when sklearn not available."""
    groups: Dict[str, List[str]] = defaultdict(list)
    for q in questions:
        first_word = q.split()[0].lower() if q.split() else "other"
        groups[first_word].append(q)

    return [
        {
            "cluster_id": idx,
            "count": len(qs),
            "questions": qs[:10],
            "representative_question": qs[0] if qs else "",
        }
        for idx, (_, qs) in enumerate(groups.items())
    ]


def get_query_trends(
    days: int = 30, group_by: str = "day", course_ids: Optional[List[int]] = None, lecture_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get query trends grouped by time period.
    
    Args:
        days: Number of days to look back
        group_by: 'day' or 'week'
        course_ids: Optional list of course IDs to filter by
    
    Returns:
        List of {period, count, questions} dicts
    """
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

    if group_by == "week":
        return _group_by_week(rows)
    else:
        return _group_by_day(rows)


def _group_by_day(rows: List[Tuple[str, datetime]]) -> List[Dict[str, Any]]:
    """Group queries by day."""
    by_day: Dict[str, List[str]] = defaultdict(list)
    for question, created_at in rows:
        day_key = created_at.strftime("%Y-%m-%d")
        by_day[day_key].append(question)

    return [
        {"period": day, "count": len(questions), "questions": questions[:5]}
        for day, questions in sorted(by_day.items())
    ]


def _group_by_week(rows: List[Tuple[str, datetime]]) -> List[Dict[str, Any]]:
    """Group queries by week."""
    by_week: Dict[str, List[str]] = defaultdict(list)
    for question, created_at in rows:
        # Get Monday of the week
        days_since_monday = created_at.weekday()
        monday = created_at - timedelta(days=days_since_monday)
        week_key = monday.strftime("%Y-%m-%d")
        by_week[week_key].append(question)

    return [
        {"period": week, "count": len(questions), "questions": questions[:5]}
        for week, questions in sorted(by_week.items())
    ]


def get_lecture_health_metrics(course_ids: Optional[List[int]] = None, lecture_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get health metrics per lecture: query count, avg complexity, confusing topics.
    
    Args:
        course_ids: Optional list of course IDs to filter by
        lecture_id: Optional lecture ID to filter by
    
    Returns:
        List of {lecture_id, lecture_name, query_count, avg_complexity, top_clusters}
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Build query for lecture stats
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
        
        if params:
            cur.execute(base_query, tuple(params))
        else:
            cur.execute(base_query)
        lecture_stats = cur.fetchall()

        # Get questions per lecture for clustering
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
        
        if params2:
            cur.execute(questions_query, tuple(params2))
        else:
            cur.execute(questions_query)
        
        questions_by_lecture: Dict[int, List[str]] = defaultdict(list)
        for row in cur.fetchall():
            lecture_id, question = row[0], row[1]
            questions_by_lecture[lecture_id].append(question)

    result = []
    for lecture_id, lecture_name, query_count in lecture_stats:
        questions = questions_by_lecture.get(lecture_id, [])
        
        # Simple complexity: average question length
        avg_complexity = (
            sum(len(q.split()) for q in questions) / len(questions)
            if questions
            else 0
        )

        # Cluster questions for this lecture
        clusters = cluster_questions(questions, n_clusters=3) if questions else []

        result.append({
            "lecture_id": lecture_id,
            "lecture_name": lecture_name,
            "query_count": query_count,
            "avg_complexity": round(avg_complexity, 1),
            "top_clusters": [
                {
                    "representative_question": c["representative_question"],
                    "count": c["count"],
                }
                for c in clusters[:3]
            ],
        })

    return result


def get_all_queries(
    limit: int = 100,
    lecture_id: Optional[int] = None,
    course_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Get all queries with filters. Returns queries from ALL students (for instructor analytics).
    
    Returns:
        List of {id, question, answer, lecture_id, lecture_name, created_at, user_id}
    """
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
            # Match course_id from either lecture's course_id OR query_history's course_id
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


def get_lecture_analytics(
    lecture_id: int,
    course_id: Optional[int],
) -> Dict[str, Any]:
    """
    Compute lecture-level analytics, including frequency polygon bins and baseline.
    Bins are computed relative to the first question timestamp for the lecture.
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT created_at, question, user_id
            FROM query_history
            WHERE lecture_id = %s
            ORDER BY created_at ASC
            """,
            (lecture_id,),
        )
        rows = cur.fetchall()

    timestamps = [row[0] for row in rows if row[0]]
    questions = [row[1] for row in rows if row[1]]
    user_ids = {row[2] for row in rows if row[2]}

    total_questions = len(timestamps)
    active_students = len(user_ids)

    top_confused_question = None
    if questions:
        counts: Dict[str, int] = defaultdict(int)
        for q in questions:
            key = q.strip().lower()
            if key:
                counts[key] += 1
        if counts:
            top_confused_question = max(counts.items(), key=lambda item: item[1])[0]

    bins: List[Dict[str, Any]] = []
    course_question_total = 0
    course_lecture_count = 0
    if not timestamps:
        return {
            "lecture_id": lecture_id,
            "total_questions": total_questions,
            "active_students": active_students,
            "peak_confusion_range": None,
            "top_confused_question": top_confused_question,
            "bins": bins,
            "course_question_total": course_question_total,
            "course_lecture_count": course_lecture_count,
        }

    duration_minutes = _estimate_duration_minutes(lecture_id)
    display_duration = max(float(BIN_SIZE_MIN), duration_minutes)
    bin_count = max(1, int(math.ceil(display_duration / BIN_SIZE_MIN)))
    lecture_counts = _count_by_minute_bins(timestamps, BIN_SIZE_MIN, bin_count)

    course_avg_counts = [0.0 for _ in range(bin_count)]
    if course_id:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT qh.lecture_id, qh.created_at
                FROM query_history qh
                JOIN lectures l ON l.id = qh.lecture_id
                WHERE l.course_id = %s
                  AND qh.lecture_id IS NOT NULL
                  AND qh.lecture_id != %s
                ORDER BY qh.lecture_id, qh.created_at ASC
                """,
                (course_id, lecture_id),
            )
            baseline_rows = cur.fetchall()

        by_lecture: Dict[int, List[datetime]] = defaultdict(list)
        for lect_id, created_at in baseline_rows:
            if created_at:
                by_lecture[lect_id].append(created_at)

        course_question_total = len(baseline_rows)
        course_lecture_count = len(by_lecture)

        if by_lecture:
            sum_counts = [0 for _ in range(bin_count)]
            lecture_count = 0
            for lect_id, times in by_lecture.items():
                if not times:
                    continue
                times.sort()
                counts = _count_by_minute_bins(times, BIN_SIZE_MIN, bin_count)
                sum_counts = [sum_counts[i] + counts[i] for i in range(bin_count)]
                lecture_count += 1

            if lecture_count > 0:
                course_avg_counts = [c / lecture_count for c in sum_counts]

    peak_idx = max(range(len(lecture_counts)), key=lambda idx: lecture_counts[idx])
    peak_start_min = peak_idx * BIN_SIZE_MIN
    peak_end_min = (peak_idx + 1) * BIN_SIZE_MIN
    peak_range = f"{peak_start_min}-{peak_end_min} min"

    for idx in range(bin_count):
        start_min = idx * BIN_SIZE_MIN
        end_min = (idx + 1) * BIN_SIZE_MIN
        start_pct = (start_min / (bin_count * BIN_SIZE_MIN)) * 100.0
        end_pct = (end_min / (bin_count * BIN_SIZE_MIN)) * 100.0
        bins.append(
            {
                "start_pct": start_pct,
                "end_pct": end_pct,
                "start_min": start_min,
                "end_min": end_min,
                "count": lecture_counts[idx],
                "course_avg": course_avg_counts[idx] if course_id else None,
            }
        )

    return {
        "lecture_id": lecture_id,
        "total_questions": total_questions,
        "active_students": active_students,
        "peak_confusion_range": peak_range,
        "top_confused_question": top_confused_question,
        "bins": bins,
        "course_question_total": course_question_total,
        "course_lecture_count": course_lecture_count,
    }

