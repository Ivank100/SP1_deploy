"""This file runs the main lecture question-answering service.
It combines retrieval, prompting, citations, and final answer assembly."""


from typing import Optional

from ...clients.openai import OpenAIClient
from ...db.postgres import (
    get_chunks_for_page,
    get_lecture_study_materials,
    insert_query,
    search_by_keywords,
    search_by_reference_patterns,
    search_similar,
)
from ...utils.citations import format_citations
from ..embeddings import embed_texts
from .constants import DEFAULT_CONTEXT_TOP_K, SYSTEM_PROMPT, strip_source_tag
from .retrieval import (
    build_keypoint_answer_prompt,
    build_page_content_answer,
    extract_explicit_page_reference,
    extract_keywords,
    extract_reference_patterns,
    is_key_points_question,
    is_page_content_request,
    select_citation_sources,
)


def _answer_key_points_question(
    client: OpenAIClient,
    question: str,
    lecture_id: int,
    course_id: Optional[int],
    user_id: Optional[int],
):
    materials = get_lecture_study_materials(lecture_id) or {}
    raw_key_points = materials.get("key_points") or []
    key_points = [point.strip() for point in raw_key_points if isinstance(point, str) and point.strip()]
    if not key_points:
        return None

    prompt, retrieval_results = build_keypoint_answer_prompt(
        question=question,
        lecture_id=lecture_id,
        course_id=course_id,
        key_points=key_points,
    )
    if not retrieval_results:
        return None

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    answer = client.chat(messages)
    answer, used_slides = strip_source_tag(answer)

    citation_sources = select_citation_sources(retrieval_results)
    citation = format_citations(citation_sources) if used_slides else ""
    answer_with_citation = f"{answer}\n\n{citation}" if citation else answer

    page_number = None
    if used_slides:
        for source in citation_sources:
            if source.get("page_number") is not None:
                page_number = source.get("page_number")
                break

    insert_query(question, answer_with_citation, lecture_id, course_id, user_id, page_number)
    return answer_with_citation, citation, citation_sources


def answer_question(
    question: str,
    lecture_id: Optional[int] = None,
    course_id: Optional[int] = None,
    top_k: int = DEFAULT_CONTEXT_TOP_K,
    user_id: Optional[int] = None,
    query_mode: Optional[str] = None,
):
    client = OpenAIClient()
    normalized_query_mode = (query_mode or "").strip().lower()

    if lecture_id is not None and (
        normalized_query_mode == "key_points" or (
            not normalized_query_mode and is_key_points_question(question)
        )
    ):
        keypoint_answer = _answer_key_points_question(
            client=client,
            question=question,
            lecture_id=lecture_id,
            course_id=course_id,
            user_id=user_id,
        )
        if keypoint_answer is not None:
            return keypoint_answer

    explicit_page = extract_explicit_page_reference(question)

    results = []
    if lecture_id is not None and explicit_page is not None:
        results = get_chunks_for_page(lecture_id, explicit_page)

        if is_page_content_request(question):
            if results:
                citation_sources = select_citation_sources(results)
                citation = format_citations(citation_sources)
                answer = build_page_content_answer(explicit_page, results)
                answer_with_citation = f"{answer}\n\n{citation}" if citation else answer
                insert_query(question, answer_with_citation, lecture_id, course_id, user_id, explicit_page)
                return answer_with_citation, citation, citation_sources

            answer = f"I couldn't find extracted content for page {explicit_page} in this lecture."
            insert_query(question, answer, lecture_id, course_id, user_id, explicit_page)
            return answer, "", []

    if not results:
        reference_patterns = extract_reference_patterns(question)
        if reference_patterns:
            results = search_by_reference_patterns(
                reference_patterns,
                top_k=max(top_k, 8),
                lecture_id=lecture_id,
                course_id=course_id,
                neighbor_window=1,
            )

    if not results:
        [q_emb] = embed_texts([question])
        results = search_similar(
            q_emb,
            top_k=top_k,
            lecture_id=lecture_id,
            course_id=course_id,
        )
        if not results:
            keywords = extract_keywords(question)
            if keywords:
                results = search_by_keywords(
                    keywords,
                    top_k=top_k,
                    lecture_id=lecture_id,
                    course_id=course_id,
                )

    if not results:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context from lecture:\n(No relevant lecture content found)\n\nQuestion: {question}"},
        ]
        answer = client.chat(messages)
        answer, _used_slides = strip_source_tag(answer)
        insert_query(question, answer, lecture_id, course_id, user_id, None)
        return answer, "", []

    context_text = "\n\n---\n\n".join(result[0] for result in results)
    citation_sources = select_citation_sources(results)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context from lecture:\n{context_text}\n\nQuestion: {question}"},
    ]
    answer = client.chat(messages)
    answer, used_slides = strip_source_tag(answer)

    citation = format_citations(citation_sources) if used_slides else ""
    answer_with_citation = f"{answer}\n\n{citation}" if citation else answer

    page_number = None
    if used_slides:
        for source in citation_sources:
            if source.get("page_number") is not None:
                if lecture_id is None or source.get("lecture_id") == lecture_id:
                    page_number = source.get("page_number")
                    break
    insert_query(question, answer_with_citation, lecture_id, course_id, user_id, page_number)

    return answer_with_citation, citation, citation_sources
