"""This file implements analytics logic for lecture insights.
It turns raw lecture or question data into summaries the API can return."""


import math
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ...db.postgres import get_conn, get_lecture, get_lecture_transcript

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
    for timestamp in timestamps:
        delta = max((timestamp - start_time).total_seconds(), 0.0)
        delta_minutes = delta / 60.0
        index = int(delta_minutes // bin_size_minutes)
        if index >= bin_count:
            index = bin_count - 1
        counts[index] += 1
    return counts


def get_lecture_analytics(
    lecture_id: int,
    course_id: Optional[int],
) -> Dict[str, Any]:
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
        for question in questions:
            key = question.strip().lower()
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
        for lecture_id_value, created_at in baseline_rows:
            if created_at:
                by_lecture[lecture_id_value].append(created_at)

        course_question_total = len(baseline_rows)
        course_lecture_count = len(by_lecture)

        if by_lecture:
            sum_counts = [0 for _ in range(bin_count)]
            lecture_count = 0
            for times in by_lecture.values():
                if not times:
                    continue
                times.sort()
                counts = _count_by_minute_bins(times, BIN_SIZE_MIN, bin_count)
                sum_counts = [sum_counts[i] + counts[i] for i in range(bin_count)]
                lecture_count += 1

            if lecture_count > 0:
                course_avg_counts = [count / lecture_count for count in sum_counts]

    peak_idx = max(range(len(lecture_counts)), key=lambda idx: lecture_counts[idx])
    peak_range = f"{peak_idx * BIN_SIZE_MIN}-{(peak_idx + 1) * BIN_SIZE_MIN} min"

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
