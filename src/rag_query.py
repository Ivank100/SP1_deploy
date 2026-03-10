# src/rag_query.py
from typing import Optional, List, Dict
from .deepseek_client import DeepSeekClient
from .db import search_similar, search_by_keywords, insert_query
from .embedding_model import embed_texts
from .citation_utils import format_citations

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

def extract_keywords(question: str, limit: int = 6) -> List[str]:
    tokens = [t.lower() for t in question.replace("?", " ").replace(".", " ").split()]
    keywords = [t for t in tokens if t not in STOP_WORDS and len(t) > 3]
    deduped = []
    for token in keywords:
        if token not in deduped:
            deduped.append(token)
    return deduped[:limit]

def answer_question(
    question: str,
    lecture_id: Optional[int] = None,
    course_id: Optional[int] = None,
    top_k: int = 5,
    user_id: Optional[int] = None,
):
    """
    Answer a question about a lecture using RAG.
    
    Args:
        question: User's question
        lecture_id: Optional lecture ID to filter search
        top_k: Number of chunks to retrieve
        
    Returns:
        Tuple of (answer, citation_string)
    """
    client = DeepSeekClient()

    # 1) embed question locally
    [q_emb] = embed_texts([question])

    # 2) retrieve similar chunks from Postgres (with page numbers)
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
    
    # Extract chunks, metadata, and lecture references
    contexts = [result[0] for result in results]  # text
    sources: List[Dict[str, Optional[int] | str | Optional[float]]] = []
    for text, page_number, lect_id, lect_name, file_type, ts_start, ts_end in results:
        sources.append(
            {
                "lecture_id": lect_id,
                "lecture_name": lect_name,
                "file_type": file_type,
                "page_number": page_number,
                "timestamp_start": ts_start,
                "timestamp_end": ts_end,
            }
        )
    context_text = "\n\n---\n\n".join(contexts)

    # 3) call DeepSeek chat for the actual answer
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
    citation = format_citations(sources) if used_slides else ""

    if citation:
        answer_with_citation = f"{answer}\n\n{citation}"
    else:
        answer_with_citation = answer

    # 6) store question and answer in database
    page_number = None
    if used_slides:
        for source in sources:
            if source.get("page_number") is not None:
                if lecture_id is None or source.get("lecture_id") == lecture_id:
                    page_number = source.get("page_number")
                    break
    insert_query(question, answer_with_citation, lecture_id, course_id, user_id, page_number)

    return answer_with_citation, citation, sources

if __name__ == "__main__":
    from .db import list_lectures
    
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
