from typing import Any, List, Optional, Tuple

from .connection import get_conn
from .schema import init_schema


def get_chunks_for_lecture(
    lecture_id: int, limit: Optional[int] = None
) -> List[Tuple[str, Optional[int], Optional[float], Optional[float]]]:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        query = """
            SELECT text, page_number, timestamp_start, timestamp_end
            FROM chunks
            WHERE lecture_id = %s
            ORDER BY chunk_index
        """
        params: List[Any] = [lecture_id]
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        cur.execute(query, tuple(params))
        return cur.fetchall()


def list_chunk_records(lecture_id: Optional[int] = None) -> List[Tuple[int, int, str]]:
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        query = "SELECT id, lecture_id, text FROM chunks"
        params: List[Any] = []
        if lecture_id is not None:
            query += " WHERE lecture_id = %s"
            params.append(lecture_id)
        query += " ORDER BY lecture_id, chunk_index"
        cur.execute(query, tuple(params))
        return cur.fetchall()


def update_chunk_embeddings(chunk_embeddings: List[Tuple[int, List[float]]]) -> None:
    if not chunk_embeddings:
        return
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        for chunk_id, emb in chunk_embeddings:
            vec_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
            cur.execute("UPDATE chunks SET embedding = %s::vector WHERE id = %s", (vec_str, chunk_id))
        conn.commit()


def clear_chunks_for_lecture(lecture_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE lecture_id = %s", (lecture_id,))
        conn.commit()


def insert_chunks(lecture_id: int, chunks_payload: List[Any], embeddings: List[List[float]]):
    assert len(chunks_payload) == len(embeddings)
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        for chunk_index, (entry, emb) in enumerate(zip(chunks_payload, embeddings)):
            if isinstance(entry, dict):
                chunk_text = entry.get("text", "")
                page_num = entry.get("page_number")
                ts_start = entry.get("timestamp_start")
                ts_end = entry.get("timestamp_end")
            else:
                chunk_text, page_num = entry
                ts_start = None
                ts_end = None

            vec_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
            cur.execute(
                """
                INSERT INTO chunks (lecture_id, page_number, chunk_index, text, embedding, timestamp_start, timestamp_end)
                VALUES (%s, %s, %s, %s, %s::vector, %s, %s)
                """,
                (lecture_id, page_num, chunk_index, chunk_text, vec_str, ts_start, ts_end),
            )
        conn.commit()


def insert_chunks_legacy(doc_id: str, chunks: List[str], embeddings: List[List[float]]):
    assert len(chunks) == len(embeddings)
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            vec_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
            cur.execute(
                """
                INSERT INTO document_chunks (doc_id, chunk_index, content, embedding)
                VALUES (%s, %s, %s, %s::vector)
                """,
                (doc_id, i, chunk, vec_str),
            )
        conn.commit()


def search_similar(
    query_emb: List[float],
    top_k: int = 5,
    lecture_id: Optional[int] = None,
    course_id: Optional[int] = None,
):
    init_schema()
    vec_str = "[" + ",".join(f"{x:.6f}" for x in query_emb) + "]"
    with get_conn() as conn, conn.cursor() as cur:
        base_query = """
            SELECT
                c.text, c.page_number, c.lecture_id, l.original_name, l.file_type,
                c.timestamp_start, c.timestamp_end,
                c.embedding <=> %s::vector AS distance
            FROM chunks c
            JOIN lectures l ON c.lecture_id = l.id
        """
        params: List[Any] = [vec_str]
        if lecture_id is not None:
            base_query += " WHERE c.lecture_id = %s"
            params.append(lecture_id)
        elif course_id is not None:
            base_query += " WHERE l.course_id = %s"
            params.append(course_id)
        base_query += " ORDER BY c.embedding <=> %s::vector LIMIT %s"
        params.extend([vec_str, top_k])
        cur.execute(base_query, tuple(params))
        return cur.fetchall()


def search_by_keywords(
    terms: List[str],
    top_k: int = 5,
    lecture_id: Optional[int] = None,
    course_id: Optional[int] = None,
):
    if not terms:
        return []
    init_schema()
    with get_conn() as conn, conn.cursor() as cur:
        base_query = """
            SELECT
                c.text, c.page_number, c.lecture_id, l.original_name, l.file_type,
                c.timestamp_start, c.timestamp_end
            FROM chunks c
            JOIN lectures l ON c.lecture_id = l.id
        """
        params: List[Any] = []
        where: List[str] = []
        if lecture_id is not None:
            where.append("c.lecture_id = %s")
            params.append(lecture_id)
        elif course_id is not None:
            where.append("l.course_id = %s")
            params.append(course_id)
        where.append("(" + " OR ".join(["c.text ILIKE %s"] * len(terms)) + ")")
        params.extend([f"%{term}%" for term in terms])
        base_query += " WHERE " + " AND ".join(where)
        base_query += " LIMIT %s"
        params.append(top_k)
        cur.execute(base_query, tuple(params))
        return cur.fetchall()


def search_similar_legacy(query_emb: List[float], top_k: int = 5):
    init_schema()
    vec_str = "[" + ",".join(f"{x:.6f}" for x in query_emb) + "]"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT content
            FROM document_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (vec_str, top_k),
        )
        return [row[0] for row in cur.fetchall()]
