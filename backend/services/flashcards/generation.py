"""This file generates flashcard candidates with the language model.
It focuses on turning lecture content into draft question-answer pairs."""


import json
import re
from typing import Any, Dict, List, Optional, Tuple

from ...clients.openai import OpenAIClient
from ...db.postgres import get_chunks_for_lecture, search_similar
from ..embeddings import embed_texts
from .constants import CANDIDATE_COUNT
from .parsing import parse_flashcard_candidates

FLASHCARD_SYSTEM_PROMPT = """You generate study flashcards.

Hard rules:
- Return JSON only. No markdown.
- Each flashcard has: question, answer, keypoint_index.
- Questions must be <= 25 words.
- Each answer MUST:
  • Clearly define the concept.
  • Explain how it works or why it matters.
  • Use specific terminology from the lecture.
  • Be 15–60 words.
  • Contain at least one concrete detail (condition, rule, step, formula, example, or constraint).
  • NEVER refer to "the lecture", "the material", or "review".
- Answers must be self-contained and useful for revision without seeing the original lecture.
- Avoid vague prompts: "explain in detail", "discuss", "describe fully", "write about"."""


def get_chunks_per_keypoint(
    lecture_id: int,
    key_points: List[str],
    chunks_per_kp: int = 2,
) -> Dict[int, List[str]]:
    """Retrieve top relevant chunks for each key point via vector search."""
    if not key_points:
        return {}
    embeddings = embed_texts(key_points)
    result: Dict[int, List[str]] = {}
    for index, embedding in enumerate(embeddings, start=1):
        rows = search_similar(embedding, top_k=chunks_per_kp, lecture_id=lecture_id)
        texts = [row[0] for row in rows if row[0]]
        if texts:
            result[index] = texts
    return result


def generate_flashcard_candidates(
    key_points: List[str],
    existing_questions: List[str],
    strategy: str = "keypoints_v1",
    candidate_count: int = CANDIDATE_COUNT,
    chunks_per_keypoint: Optional[Dict[int, List[str]]] = None,
) -> List[Dict[str, Any]]:
    """Generate flashcard candidates using the LLM."""
    client = OpenAIClient()
    key_points_text = _format_key_points_with_context(key_points, chunks_per_keypoint)
    existing_questions_text = ""
    if existing_questions:
        existing_questions_text = (
            "\n\nAvoid repeating these existing questions (semantic duplicates also):\n"
            + "\n".join(f"- {question}" for question in existing_questions[:10])
        )

    focus_instruction = ""
    if "definitions" in strategy:
        focus_instruction = "\nFocus on definitions and distinctions. Avoid process/step questions unless necessary."
    elif "process" in strategy:
        focus_instruction = "\nFocus on processes and steps. Prefer 'how' questions about procedures."

    grounding_instruction = ""
    if chunks_per_keypoint:
        grounding_instruction = (
            "\n\nBase each answer STRICTLY on the provided context excerpts. "
            "Do not invent details not present in the excerpts."
        )

    user_prompt = f"""Create {candidate_count} flashcard CANDIDATES from these key points.

Key points (with context excerpts when provided):
{key_points_text}{existing_questions_text}{grounding_instruction}{focus_instruction}

Return JSON array:
[
  {{"question":"...", "answer":"...", "keypoint_index": 3}},
  ...
]"""

    response = client.chat(
        _build_flashcard_messages(
            user_prompt,
            extra_system_rules="\n- Generate exactly N flashcard candidates (not final selection).\n- Each flashcard must test ONE concept.\n- No citations, no page numbers, no timestamps.",
        ),
        temperature=0.7,
    ).strip()
    candidates = parse_flashcard_candidates(response, key_points, candidate_count)
    if candidates:
        return candidates

    fallback_prompt = _build_fallback_prompt(candidate_count, key_points_text)
    response = client.chat(
        [
            {"role": "system", "content": "You create flashcards from key points."},
            {"role": "user", "content": fallback_prompt},
        ],
        temperature=0.5,
    ).strip()
    candidates = parse_flashcard_candidates(response, key_points, candidate_count)
    if not candidates:
        raise ValueError("No flashcard candidates could be parsed from model response")
    return candidates


def fill_missing_flashcards(
    key_points: List[str],
    already_selected: List[Dict[str, Any]],
    missing_count: int,
    chunks_per_keypoint: Optional[Dict[int, List[str]]] = None,
) -> List[Dict[str, Any]]:
    """Generate additional flashcards to fill missing slots."""
    client = OpenAIClient()
    key_points_text = _format_key_points_with_context(key_points, chunks_per_keypoint)
    existing_questions_text = "\n".join(
        f"- {candidate.get('question', '')}" for candidate in already_selected
    )

    user_prompt = f"""You must generate {missing_count} additional flashcards.

Do NOT repeat or paraphrase any of these questions:
{existing_questions_text}

Use these key points:
{key_points_text}
""" + (
        "\nBase each answer STRICTLY on the provided context excerpts." if chunks_per_keypoint else ""
    ) + """

Return JSON array only."""

    response = client.chat(
        _build_flashcard_messages(user_prompt),
        temperature=0.8,
    ).strip()
    candidates = parse_flashcard_candidates(response, key_points, missing_count)
    if candidates:
        return candidates

    fallback_prompt = _build_fallback_prompt(missing_count, key_points_text, additional=True)
    response = client.chat(
        [
            {"role": "system", "content": "You create flashcards from key points."},
            {"role": "user", "content": fallback_prompt},
        ],
        temperature=0.5,
    ).strip()
    candidates = parse_flashcard_candidates(response, key_points, missing_count)
    if not candidates:
        raise ValueError("No flashcards could be parsed from model response")
    return candidates


def prepare_context_for_chunks(lecture_id: int):
    """Get chunks for lecture for grounded flashcard fallback."""
    chunks = get_chunks_for_lecture(lecture_id, limit=60)
    if not chunks:
        raise ValueError("No chunks found for lecture")
    return chunks


def generate_flashcards_from_chunks(
    chunks: List[Tuple[str, Optional[int], Optional[float], Optional[float]]],
    existing_questions: List[str],
) -> List[Dict[str, Any]]:
    """Generate grounded flashcards directly from lecture chunks."""
    if not chunks or len(chunks) < 3:
        raise ValueError("Not enough chunks for flashcard generation")

    selected_chunks, chunk_refs = _select_spread_chunks(chunks)
    context = "\n\n".join(selected_chunks)
    client = OpenAIClient()
    existing_text = ""
    if existing_questions:
        existing_text = "\n\nAvoid repeating: " + "; ".join(existing_questions[:5])

    response = client.chat(
        [
            {
                "role": "system",
                "content": (
                    "You create study flashcards from lecture excerpts. Each answer must: "
                    "define the concept, explain how it works or why it matters, use specific terminology, "
                    "be 15-60 words, include at least one concrete detail. "
                    "Never refer to 'the lecture', 'the material', or 'review'. Base answers strictly on the context."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Create 10 flashcards from this lecture context. Base each answer strictly on the excerpts. "
                    "Each answer: define the concept, explain how/why, use lecture terms, include a concrete detail (15-60 words). "
                    "Return JSON array: [{\"question\":\"...\", \"answer\":\"...\", \"source_ref\":\"Page 3\"}]. "
                    f"Use source_ref from context markers (e.g. [Page N] or [Time MM:SS]).{existing_text}\n\n"
                    f"Context:\n{context}\n\nJSON array:"
                ),
            },
        ],
        temperature=0.5,
        max_tokens=800,
    ).strip()
    return _parse_chunk_response(response, chunk_refs)


def expand_keypoint_to_answer(keypoint: str, question: str) -> str:
    """Use the LLM to create an informative answer from a key point."""
    try:
        client = OpenAIClient()
        messages = [
            {
                "role": "system",
                "content": (
                    "You provide informative definitions for study flashcards. "
                    "Each answer must: define the concept, explain how it works or why it matters, "
                    "use specific terminology, include at least one concrete detail. "
                    "Be 15-60 words. Never refer to 'the lecture', 'the material', or 'review'."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Key point: {keypoint}\n\nQuestion: {question}\n\n"
                    "Provide a clear, informative answer (15-60 words) that defines the concept and explains how/why it matters:"
                ),
            },
        ]
        response = client.chat(messages, temperature=0.3).strip()
        if response:
            return response[:500]
        messages[1]["content"] = (
            f"Define {keypoint} in 15-40 words. Include how it works or an example. "
            "Never say 'review the material'."
        )
        response = client.chat(messages, temperature=0.2).strip()
        if response:
            return response[:400]
    except Exception:
        pass
    raise ValueError("Cannot generate informative answer from keypoint alone")


def _format_key_points_with_context(
    key_points: List[str],
    chunks_per_keypoint: Optional[Dict[int, List[str]]],
) -> str:
    parts = []
    for index, key_point in enumerate(key_points, start=1):
        parts.append(f"{index}) {key_point}")
        if chunks_per_keypoint and index in chunks_per_keypoint:
            for excerpt_index, excerpt in enumerate(chunks_per_keypoint[index][:2], start=1):
                suffix = "..." if len(excerpt) > 500 else ""
                parts.append(f"   Context {excerpt_index}: {excerpt[:500]}{suffix}")
    return "\n".join(parts)


def _build_flashcard_messages(
    user_prompt: str,
    extra_system_rules: str = "",
) -> List[Dict[str, str]]:
    return [
        {
            "role": "system",
            "content": f"{FLASHCARD_SYSTEM_PROMPT}{extra_system_rules}",
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


def _build_fallback_prompt(
    count: int,
    key_points_text: str,
    additional: bool = False,
) -> str:
    qualifier = "additional " if additional else ""
    return f"""Create {count} {qualifier}flashcards using this format only:
Q: <question>
A: <informative answer - 15-60 words, define the concept, explain how/why, use lecture terminology, include at least one concrete detail>

Use these key points:
{key_points_text}

Each answer must: define the concept, explain how it works or why it matters, use specific terms, include a concrete detail. Never say "review the material" or "see the lecture".
Return ONLY Q/A lines, no JSON, no markdown."""


def _select_spread_chunks(
    chunks: List[Tuple[str, Optional[int], Optional[float], Optional[float]]]
) -> Tuple[List[str], List[str]]:
    count = min(8, len(chunks))
    step = max(1, (len(chunks) - 1) // (count - 1)) if count > 1 else 0
    selected_indices = [index * step for index in range(count)] if step > 0 else list(range(count))
    selected_indices = [min(index, len(chunks) - 1) for index in selected_indices]

    context_parts = []
    chunk_refs = []
    for index in selected_indices:
        text, page, ts_start, ts_end = chunks[index]
        ref = f"[Page {page}]" if page else (f"[Time {ts_start}-{ts_end}]" if ts_start and ts_end else "[Chunk]")
        context_parts.append(f"{ref} {text.strip()}")
        chunk_refs.append(ref)
    return context_parts, chunk_refs


def _parse_chunk_response(response: str, chunk_refs: List[str]) -> List[Dict[str, Any]]:
    cleaned = re.sub(r"^```(?:json)?\s*", "", response)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned).strip()

    candidates = []
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return candidates

    if not isinstance(parsed, list):
        return candidates

    for index, item in enumerate(parsed[:12]):
        if not isinstance(item, dict):
            continue
        question = item.get("question") or item.get("front") or ""
        answer = item.get("answer") or item.get("back") or ""
        source_ref = item.get("source_ref") or (chunk_refs[index % len(chunk_refs)] if chunk_refs else None)
        if question and answer:
            candidates.append(
                {
                    "question": str(question).strip(),
                    "answer": str(answer).strip(),
                    "keypoint_index": None,
                    "source_ref": source_ref,
                }
            )
    return candidates
