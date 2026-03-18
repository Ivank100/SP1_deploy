"""This file generates lecture summaries.
It condenses lecture content into a shorter study guide for students."""


from ...clients.openai import OpenAIClient
from ...db.postgres import save_lecture_summary
from .shared import ensure_ready_lecture, prepare_context


def generate_summary(lecture_id: int) -> str:
    ensure_ready_lecture(lecture_id)
    context, _chunks = prepare_context(lecture_id)
    client = OpenAIClient()
    messages = [
        {
            "role": "system",
            "content": "You create concise study summaries from lecture excerpts.",
        },
        {
            "role": "user",
            "content": (
                "Create a clear summary (3-5 short paragraphs) of the following lecture context. "
                "Do not introduce information that is not in the text.\n\n"
                f"Context:\n{context}\n\nSummary:"
            ),
        },
    ]
    summary = client.chat(messages, max_tokens=303).strip()
    save_lecture_summary(lecture_id, summary)
    return summary
