# src/rag_query.py
from typing import Optional, List, Dict
from .deepseek_client import DeepSeekClient
from .db import search_similar, insert_query
from .embedding_model import embed_texts
from .citation_utils import format_citations

SYSTEM_PROMPT = """You are a helpful assistant answering questions based only on the provided context from PDF lectures. 
If the answer is not in the context, say you don't know.
When referencing information, mention the page numbers, and if multiple lectures are involved, name the lecture alongside the page."""

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
        answer = "I couldn't find any relevant information in the lecture materials."
        insert_query(question, answer, lecture_id, course_id, user_id)
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
    
    # 4) format citations
    citation = format_citations(sources)
    
    # 5) append citation to answer if available
    if citation:
        answer_with_citation = f"{answer}\n\n{citation}"
    else:
        answer_with_citation = answer
    
    # 6) store question and answer in database
    insert_query(question, answer_with_citation, lecture_id, course_id, user_id)
    
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
