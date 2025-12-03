# src/analytics.py
"""
Analytics utilities for instructor dashboard: clustering, trends, metrics.
"""
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import json

from .db import get_conn, get_lecture, list_lectures
from .embedding_model import embed_texts


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

