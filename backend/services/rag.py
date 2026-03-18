# src/rag_query.py
from collections import defaultdict
import re
from typing import Optional, List, Dict, Tuple, Any
from ..clients.openai import OpenAIClient
from ..db.postgres import (
    get_chunks_for_page,
    get_lecture_study_materials,
    insert_query,
    search_by_keywords,
    search_by_reference_patterns,
    search_similar,
)
from .embeddings import embed_texts
from ..utils.citations import format_citations

SYSTEM_PROMPT = """You are a helpful assistant for students studying lecture material.
You are given context extracted from lecture slides or PDFs. Use this context as your primary source.
If the answer is not covered in the context, answer using your general knowledge — do not refuse or say you don't know.
Do not include page numbers or source references in your answer — citations are handled separately.

IMPORTANT: Start your response with exactly one of these two tags (then a newline), before writing anything else:
[FROM_SLIDES] — if your answer is based on the provided lecture context
[GENERAL] — if your answer is based on your general knowledge because the context did not cover the question"""

STOP_WORDS = {
    "the", "a", "an", "is", "are", "to", "of", "in", "on", "for", "and", "or", "with",
    "what", "why", "how", "when", "where", "who", "which", "can", "could", "should", "would",
}

DEFAULT_CONTEXT_TOP_K = 10
DEFAULT_CITATION_TOP_K = 3
DEFAULT_CITATION_MAX_DISTANCE = 0.35

REFERENCE_PATTERNS = (
    r"\bquestion\s*(\d{1,3})\b",
    r"\bq(?:uestion)?\s*#?\s*(\d{1,3})\b",
    r"\bpage\s*(\d{1,4})\b",
    r"\bslide\s*(\d{1,4})\b",
)

PAGE_LOOKUP_PATTERNS = (
    r"\bpage\s*(\d{1,4})\b",
    r"\bslide\s*(\d{1,4})\b",
)

PAGE_CONTENT_HINT_PATTERNS = (
    r"\bcontent(?:s)?\b",
    r"\btext\b",
    r"\bwhat(?:'s|\s+is)?\s+on\b",
    r"\bwhat\s+does\b",
    r"\bsay\b",
    r"\bshow\b",
    r"\bgive\b",
    r"\bdisplay\b",
    r"\bextract\b",
    r"\bread\b",
    r"\bfull\b",
)

KEYPOINT_QUESTION_PATTERNS = (
    r"\bkey\s*points?\b",
    r"\bmain\s*points?\b",
    r"\bimportant\s*points?\b",
    r"\bkey\s*concepts?\b",
    r"\bmain\s*concepts?\b",
)

def extract_keywords(question: str, limit: int = 6) -> List[str]:
    tokens = [t.lower() for t in question.replace("?", " ").replace(".", " ").split()]
    keywords = [t for t in tokens if t not in STOP_WORDS and len(t) > 3]
    deduped = []
    for token in keywords:
        if token not in deduped:
            deduped.append(token)
    return deduped[:limit]


def _normalize_result(result: Tuple[Any, ...]) -> Dict[str, Any]:
    text, page_number, lect_id, lect_name, file_type, ts_start, ts_end, *rest = result
    distance = rest[0] if rest else None
    return {
        "text": text,
        "lecture_id": lect_id,
        "lecture_name": lect_name,
        "file_type": file_type,
        "page_number": page_number,
        "timestamp_start": ts_start,
        "timestamp_end": ts_end,
        "distance": distance,
    }


def _build_sources(
    results: List[Dict[str, Any]]
) -> List[Dict[str, Optional[int] | str | Optional[float]]]:
    sources: List[Dict[str, Optional[int] | str | Optional[float]]] = []
    for result in results:
        sources.append(
            {
                "lecture_id": result["lecture_id"],
                "lecture_name": result["lecture_name"],
                "file_type": result["file_type"],
                "page_number": result["page_number"],
                "timestamp_start": result["timestamp_start"],
                "timestamp_end": result["timestamp_end"],
            }
        )
    return sources


def _select_citation_sources(
    results: List[Tuple[Any, ...]],
    limit: int = DEFAULT_CITATION_TOP_K,
) -> List[Dict[str, Optional[int] | str | Optional[float]]]:
    normalized_results = [_normalize_result(result) for result in results]
    if not normalized_results:
        return []

    best_distance = min(
        result["distance"] for result in normalized_results if result["distance"] is not None
    ) if any(result["distance"] is not None for result in normalized_results) else None

    page_scores: Dict[Tuple[Any, ...], float] = defaultdict(float)
    best_result_by_ref: Dict[Tuple[Any, ...], Dict[str, Any]] = {}

    for result in normalized_results:
        if not result["text"].strip():
            continue
        ref_key = (
            result["lecture_id"],
            result["page_number"],
            result["timestamp_start"],
            result["timestamp_end"],
        )
        distance = result["distance"]
        if distance is not None and best_distance is not None:
            if distance > max(DEFAULT_CITATION_MAX_DISTANCE, best_distance + 0.12):
                continue
            score = 1.0 / max(distance + 1e-6, 1e-6)
        else:
            score = 1.0

        page_scores[ref_key] += score
        current_best = best_result_by_ref.get(ref_key)
        if current_best is None or (
            distance is not None and (
                current_best["distance"] is None or distance < current_best["distance"]
            )
        ):
            best_result_by_ref[ref_key] = result

    ranked_refs = sorted(
        page_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    selected_results = []
    for ref_key, _score in ranked_refs:
        result = best_result_by_ref[ref_key]
        if result in selected_results:
            continue
        selected_results.append(result)
        if len(selected_results) >= limit:
            break

    return _build_sources(selected_results)


def extract_reference_patterns(question: str) -> List[str]:
    """
    Build regexes for explicit document references like "question 20" or "page 4".
    These are better served by targeted text lookup than semantic similarity.
    """
    patterns: List[str] = []
    lowered = question.lower()

    for raw_pattern in REFERENCE_PATTERNS:
        for match in re.finditer(raw_pattern, lowered):
            ref_num = match.group(1)
            prefix = lowered[match.start():match.end()].split()[0]
            if prefix.startswith("q"):
                patterns.extend(
                    [
                        rf"\bquestion\s*[:.#-]?\s*{ref_num}\b",
                        rf"\bq\s*[:.#-]?\s*{ref_num}\b",
                        rf"\b{ref_num}\s*[\).:-]",
                    ]
                )
            elif prefix == "page":
                patterns.append(rf"\bpage\s*[:.#-]?\s*{ref_num}\b")
            elif prefix == "slide":
                patterns.append(rf"\bslide\s*[:.#-]?\s*{ref_num}\b")

    deduped: List[str] = []
    for pattern in patterns:
        if pattern not in deduped:
            deduped.append(pattern)
    return deduped


def extract_explicit_page_reference(question: str) -> Optional[int]:
    lowered = question.lower()
    matches: List[int] = []
    for pattern in PAGE_LOOKUP_PATTERNS:
        matches.extend(int(match.group(1)) for match in re.finditer(pattern, lowered))

    unique_matches = sorted(set(matches))
    if len(unique_matches) == 1:
        return unique_matches[0]
    return None


def is_page_content_request(question: str) -> bool:
    lowered = question.lower()
    has_page_ref = extract_explicit_page_reference(question) is not None
    if not has_page_ref:
        return False
    return any(re.search(pattern, lowered) for pattern in PAGE_CONTENT_HINT_PATTERNS)


def _build_page_content_answer(
    page_number: int,
    results: List[Tuple[Any, ...]],
) -> str:
    parts: List[str] = []
    for result in results:
        text = str(result[0]).strip()
        if text:
            parts.append(text)

    body = "\n\n".join(parts).strip()
    if not body:
        return f"I found page {page_number}, but it does not contain extracted text."
    return f"Here is the extracted content from page {page_number}:\n\n{body}"


def is_key_points_question(question: str) -> bool:
    lowered = question.lower()
    return any(re.search(pattern, lowered) for pattern in KEYPOINT_QUESTION_PATTERNS)


def _extract_requested_keypoint_numbers(question: str, total_keypoints: int) -> List[int]:
    if total_keypoints <= 0:
        return []

    matches: List[int] = []
    for match in re.finditer(r"\b(?:key\s*point|point|concept)\s*(\d{1,2})\b", question.lower()):
        value = int(match.group(1))
        if 1 <= value <= total_keypoints:
            matches.append(value)

    deduped: List[int] = []
    for value in matches:
        if value not in deduped:
            deduped.append(value)
    return deduped


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

    requested_numbers = _extract_requested_keypoint_numbers(question, len(key_points))
    if requested_numbers:
        selected = [(index, key_points[index - 1]) for index in requested_numbers]
    else:
        selected = list(enumerate(key_points, start=1))

    retrieval_results: List[Tuple[Any, ...]] = []
    selected_with_results: List[Tuple[int, str, List[Tuple[Any, ...]]]] = []
    for keypoint_index, key_point in selected:
        [keypoint_embedding] = embed_texts([key_point])
        keypoint_results = search_similar(
            keypoint_embedding,
            top_k=2,
            lecture_id=lecture_id,
            course_id=course_id,
        )
        selected_with_results.append((keypoint_index, key_point, keypoint_results))
        for result in keypoint_results:
            if result not in retrieval_results:
                retrieval_results.append(result)

    if not retrieval_results:
        return None

    keypoint_lines = [f"{index}. {text}" for index, text in selected]
    context_sections: List[str] = []
    for index, key_point, related_chunks in selected_with_results:
        excerpt_lines = [f"- {str(chunk[0]).strip()}" for chunk in related_chunks if str(chunk[0]).strip()]
        section = [f"Key point {index}: {key_point}"]
        if excerpt_lines:
            section.append("Related lecture excerpts:")
            section.extend(excerpt_lines)
        context_sections.append("\n".join(section))
    lecture_support = "\n\n".join(context_sections)

    prompt = (
        "These key points were previously generated for this lecture.\n\n"
        f"Stored key points:\n" + "\n".join(keypoint_lines) + "\n\n"
        "Use the lecture excerpts to elaborate on the relevant key points.\n"
        "Keep the explanation grounded in the provided excerpts, organize it clearly, and make it useful for studying.\n"
        "If the user asks about specific numbered key points, focus on those.\n\n"
        f"Question: {question}\n\n"
        f"Lecture support:\n{lecture_support}"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    answer = client.chat(messages)

    used_slides = True
    if answer.startswith("[FROM_SLIDES]"):
        answer = answer[len("[FROM_SLIDES]"):].lstrip("\n")
    elif answer.startswith("[GENERAL]"):
        answer = answer[len("[GENERAL]"):].lstrip("\n")
        used_slides = False

    citation_sources = _select_citation_sources(retrieval_results)
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
    """
    Answer a question about a lecture using RAG.
    
    Args:
        question: User's question
        lecture_id: Optional lecture ID to filter search
        top_k: Number of chunks to retrieve for answer context
        
    Returns:
        Tuple of (answer, citation_string)
    """
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
                citation_sources = _select_citation_sources(results)
                citation = format_citations(citation_sources)
                answer = _build_page_content_answer(explicit_page, results)
                answer_with_citation = f"{answer}\n\n{citation}" if citation else answer
                insert_query(question, answer_with_citation, lecture_id, course_id, user_id, explicit_page)
                return answer_with_citation, citation, citation_sources

            answer = f"I couldn't find extracted content for page {explicit_page} in this lecture."
            insert_query(question, answer, lecture_id, course_id, user_id, explicit_page)
            return answer, "", []

    # 1) try targeted retrieval for explicit document references like "question 20"
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

    # 2) fall back to semantic/vector retrieval
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
        if answer.startswith("[FROM_SLIDES]"):
            answer = answer[len("[FROM_SLIDES]"):].lstrip("\n")
        elif answer.startswith("[GENERAL]"):
            answer = answer[len("[GENERAL]"):].lstrip("\n")
        insert_query(question, answer, lecture_id, course_id, user_id, None)
        return answer, "", []
    
    # Extract broader answer context from the retrieved chunks.
    contexts = [result[0] for result in results]  # text
    context_text = "\n\n---\n\n".join(contexts)
    citation_sources = _select_citation_sources(results)

    # 3) call the OpenAI-compatible chat API for the actual answer
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context from lecture:\n{context_text}\n\nQuestion: {question}"},
    ]
    answer = client.chat(messages)

    # 4) strip the source tag and decide whether to show citations
    used_slides = True
    if answer.startswith("[FROM_SLIDES]"):
        answer = answer[len("[FROM_SLIDES]"):].lstrip("\n")
    elif answer.startswith("[GENERAL]"):
        answer = answer[len("[GENERAL]"):].lstrip("\n")
        used_slides = False

    # 5) format and attach citations only when the answer came from the slides
    citation = format_citations(citation_sources) if used_slides else ""

    if citation:
        answer_with_citation = f"{answer}\n\n{citation}"
    else:
        answer_with_citation = answer

    # 6) store question and answer in database
    page_number = None
    if used_slides:
        for source in citation_sources:
            if source.get("page_number") is not None:
                if lecture_id is None or source.get("lecture_id") == lecture_id:
                    page_number = source.get("page_number")
                    break
    insert_query(question, answer_with_citation, lecture_id, course_id, user_id, page_number)

    return answer_with_citation, citation, citation_sources

if __name__ == "__main__":
    from ..db.postgres import list_lectures
    
    # List available lectures
    lectures = list_lectures()
    if lectures:
        print("Available lectures:")
        for lect in lectures:
            print(f"  [{lect[0]}] {lect[1]} ({lect[3]} pages, status: {lect[4]})")
        print()
        try:
            lecture_id = int(input("Enter lecture ID (or press Enter to search all): ").strip() or "0")
            if lecture_id == 0:
                lecture_id = None
        except ValueError:
            lecture_id = None
    else:
        print("No lectures found. Please ingest a PDF first.")
        lecture_id = None
    
    print()
    while True:
        q = input("Question (empty to quit): ").strip()
        if not q:
            break
        answer, citation, sources = answer_question(q, lecture_id=lecture_id)
        print("Answer:\n", answer)
        if citation:
            print(f"\nCitation: {citation}")
        if sources:
            print("\nSources:")
            for src in sources:
                print(f"- {src['lecture_name']} (page {src['page_number']})")
        print()
