# src/rag_query.py
from .deepseek_client import DeepSeekClient
from .db import search_similar
from .embedding_model import embed_texts

SYSTEM_PROMPT = """You are a helpful assistant answering questions based only on the provided context from a PDF. 
If the answer is not in the context, say you don't know."""

def answer_question(question: str, top_k: int = 5) -> str:
    client = DeepSeekClient()

    # 1) embed question locally
    [q_emb] = embed_texts([question])

    # 2) retrieve similar chunks from Postgres
    contexts = search_similar(q_emb, top_k=top_k)
    context_text = "\n\n---\n\n".join(contexts)

    # 3) call DeepSeek chat for the actual answer
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {question}"},
    ]
    return client.chat(messages)

if __name__ == "__main__":
    while True:
        q = input("Question (empty to quit): ").strip()
        if not q:
            break
        print("Answer:\n", answer_question(q))
        print()
