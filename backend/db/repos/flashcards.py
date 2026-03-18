import json
from typing import Any, Dict, List, Optional, Tuple

from ..connection import get_conn


def list_flashcards(lecture_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'flashcards'
            AND column_name = 'question'
        """)
        has_new_schema = bool(cur.fetchone())
        if has_new_schema:
            cur.execute(
                """
                SELECT f.id, f.question, f.answer, NULL as page_number
                FROM flashcards f
                WHERE f.lecture_id = %s
                ORDER BY f.created_at DESC
                LIMIT 100
                """,
                (lecture_id,),
            )
        else:
            cur.execute(
                """
                SELECT id, front, back, page_number
                FROM flashcards
                WHERE lecture_id = %s
                ORDER BY id
                """,
                (lecture_id,),
            )
        return cur.fetchall()


def replace_flashcards(lecture_id: int, cards: List[Tuple[str, str, Optional[int]]]):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO flashcard_sets (lecture_id, strategy)
            VALUES (%s, 'legacy_v1')
            RETURNING id
        """, (lecture_id,))
        set_row = cur.fetchone()
        set_id = set_row[0] if set_row else None
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'flashcards' AND column_name = 'front'")
        has_old = bool(cur.fetchone())
        cur.execute("DELETE FROM flashcards WHERE lecture_id = %s", (lecture_id,))
        if has_old:
            for front, back, page in cards:
                cur.execute(
                    """
                    INSERT INTO flashcards (lecture_id, front, back, page_number)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (lecture_id, front, back, page),
                )
        else:
            for front, back, _ in cards:
                cur.execute(
                    """
                    INSERT INTO flashcards (lecture_id, flashcard_set_id, question, answer)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (lecture_id, set_id, front, back),
                )
        conn.commit()


def create_flashcard_set(
    lecture_id: int,
    strategy: str = "keypoints_v1",
    created_by_user_id: Optional[int] = None,
    seed: Optional[int] = None,
) -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO flashcard_sets (lecture_id, created_by_user_id, strategy, seed)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (lecture_id, created_by_user_id, strategy, seed),
        )
        set_id = cur.fetchone()[0]
        conn.commit()
        return set_id


def insert_flashcards(flashcard_set_id: int, lecture_id: int, flashcards: List[Dict[str, Any]]):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'flashcards'")
        columns = {row[0] for row in cur.fetchall()}
        has_question = "question" in columns
        has_answer = "answer" in columns
        has_front = "front" in columns
        has_back = "back" in columns
        has_page_number = "page_number" in columns
        has_source_keypoint_id = "source_keypoint_id" in columns
        has_source_chunk_ids = "source_chunk_ids" in columns
        has_quality_score = "quality_score" in columns

        inserted = 0
        for card in flashcards:
            front = (card.get("front") or card.get("question") or "").strip()
            back = (card.get("back") or card.get("answer") or "").strip()
            if not front or not back:
                continue
            cols = ["flashcard_set_id", "lecture_id"]
            vals: List[Any] = [flashcard_set_id, lecture_id]
            if has_question:
                cols.append("question")
                vals.append(front)
            if has_answer:
                cols.append("answer")
                vals.append(back)
            if has_front:
                cols.append("front")
                vals.append(front)
            if has_back:
                cols.append("back")
                vals.append(back)
            if has_page_number:
                cols.append("page_number")
                vals.append(card.get("page_number"))
            if has_source_keypoint_id:
                cols.append("source_keypoint_id")
                vals.append(card.get("source_keypoint_id"))
            if has_source_chunk_ids:
                cols.append("source_chunk_ids")
                vals.append(json.dumps(card.get("source_chunk_ids")) if card.get("source_chunk_ids") else None)
            if has_quality_score:
                cols.append("quality_score")
                vals.append(card.get("quality_score"))

            placeholders = ", ".join(["%s"] * len(cols))
            cur.execute(f"INSERT INTO flashcards ({', '.join(cols)}) VALUES ({placeholders})", vals)
            inserted += 1
        if inserted == 0:
            raise ValueError("No valid flashcards to insert")
        conn.commit()


def get_latest_flashcard_set(lecture_id: int) -> Optional[Tuple[int, str, Optional[int]]]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, strategy, created_by_user_id
            FROM flashcard_sets
            WHERE lecture_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (lecture_id,),
        )
        row = cur.fetchone()
        return row if row else None


def get_flashcard_set_by_id(set_id: int) -> Optional[Tuple[int, int, str, Optional[int]]]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, lecture_id, strategy, created_by_user_id
            FROM flashcard_sets
            WHERE id = %s
            """,
            (set_id,),
        )
        return cur.fetchone()


def list_flashcards_by_set(set_id: int) -> List[Tuple[int, str, str, Optional[int], Optional[float]]]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'flashcards'")
        columns = {row[0] for row in cur.fetchall()}
        has_question = "question" in columns
        has_answer = "answer" in columns
        has_front = "front" in columns
        has_back = "back" in columns
        has_source_keypoint_id = "source_keypoint_id" in columns
        has_quality_score = "quality_score" in columns
        question_expr = "COALESCE(NULLIF(question, ''), front)" if has_question and has_front else ("question" if has_question else "front")
        answer_expr = "COALESCE(NULLIF(answer, ''), back)" if has_answer and has_back else ("answer" if has_answer else "back")
        source_expr = "source_keypoint_id" if has_source_keypoint_id else "NULL"
        quality_expr = "quality_score" if has_quality_score else "NULL"
        cur.execute(
            f"""
            SELECT id, {question_expr} as question, {answer_expr} as answer, {source_expr} as source_keypoint_id, {quality_expr} as quality_score
            FROM flashcards
            WHERE flashcard_set_id = %s
            ORDER BY {quality_expr} DESC NULLS LAST, id
            """,
            (set_id,),
        )
        return cur.fetchall()


def get_previous_flashcard_questions(lecture_id: int, limit_sets: int = 3) -> List[str]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT f.question
            FROM flashcards f
            JOIN flashcard_sets fs ON f.flashcard_set_id = fs.id
            WHERE fs.lecture_id = %s
            AND fs.id IN (
                SELECT id FROM flashcard_sets
                WHERE lecture_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            )
            """,
            (lecture_id, lecture_id, limit_sets),
        )
        return [row[0] for row in cur.fetchall()]
