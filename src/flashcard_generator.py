"""
Flashcard generation pipeline with validation, deduplication, and quality control.
Generates exactly 5 high-quality flashcards per set.
"""
import json
import re
import random
from typing import List, Dict, Any, Tuple, Optional, Set
import numpy as np

from .deepseek_client import DeepSeekClient
from .embedding_model import embed_texts
from .db import (
    get_lecture,
    get_lecture_study_materials,
    get_previous_flashcard_questions,
    get_chunks_for_lecture,
    search_similar,
)
from .study_materials import generate_key_points as _generate_key_points


# Hard limits - relaxed for better study cards
MAX_QUESTION_WORDS = 25
MAX_ANSWER_WORDS = 80  # Allow 2-4 sentences (was 60)
CANDIDATE_COUNT = 12
FINAL_COUNT = 5
MAX_SIMILARITY_THRESHOLD = 0.90

# Banned phrases - allow "why" and "how" (good for learning), disallow vague prompts
BANNED_QUESTION_PATTERNS = [
    r'\bexplain\s+(?:in\s+)?detail\b',
    r'\bdescribe\s+(?:fully|in\s+detail)\b',
    r'\bdiscuss\b',
    r'\belaborate\b',
    r'\bhow would you\b',
    r'\bwhat do you think\b',
    r'\bin your opinion\b',
    r'\bhow do you feel\b',
    r'\bwrite about\b',
]

VAGUE_ANSWER_PATTERNS = [
    r'\bvarious\b',
    r'\bseveral\b',
    r'\bit depends\b',
]

# Meta-references that defer teaching (reject)
META_REFERENCE_PATTERNS = [
    r'\breview\b',
    r'\bsee\s+(?:the\s+)?lecture\b',
    r'\bthe\s+material\b',
    r'\bas\s+discussed\b',
    r'\brefer\s+to\s+(?:the\s+)?(?:lecture|material)\b',
]

# Mechanism indicators (at least one required for informative answers)
MECHANISM_INDICATORS = [
    r'\bif\b', r'\bwhen\b', r'\bbecause\b', r'\brequires\b', r'\bcauses\b',
    r'\buses\b', r'\bconsists\b', r'\bdefined\s+as\b', r'\bsuch\s+as\b',
    r'\bfor\s+example\b', r'\be\.g\.\b', r'\blike\b',
]

# Answer must not simply echo the question (e.g. Q: "What is X?" A: "X")
def answer_echoes_question(question: str, answer: str) -> bool:
    """Check if answer is just restating the question without adding information."""
    q_lower = question.lower().strip()
    a_lower = answer.lower().strip()
    a_word_list = a_lower.split()
    # Only reject obvious echoes: answer is nearly identical to question subject
    for prefix in ['what is ', 'what are ', 'what was ', 'what were ', 'who is ', 'who are ',
                   'where is ', 'where are ', 'define ']:
        if q_lower.startswith(prefix):
            subject = q_lower[len(prefix):].rstrip('?').strip()
            # Clear echo: answer equals subject or subject + max 2 trivial words
            if a_lower == subject:
                return True
            if len(a_word_list) <= len(subject.split()) + 2:
                # Check if extra words add meaning
                subject_words = set(subject.split())
                trivial = {'the', 'a', 'an', 'is', 'are'}
                extra = set(a_word_list) - subject_words - trivial
                if len(extra) == 0:
                    return True
            break
    return False


def normalize_text(text: str) -> str:
    """Normalize text for duplicate detection."""
    # Lowercase, trim, collapse spaces, remove punctuation
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def contains_banned_phrase(text: str, patterns: List[str]) -> bool:
    """Check if text contains any banned phrase."""
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in patterns)


def validate_flashcard(question: str, answer: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a single flashcard candidate.
    Returns (is_valid, error_message).
    """
    q_text = (question or "").strip()
    a_text = (answer or "").strip()
    q_words = count_words(q_text)
    a_words = count_words(a_text)
    if q_words < 2 or a_words < 1:
        return False, "Question/answer too short"
    if not re.search(r"[a-zA-Z0-9]", q_text) or not re.search(r"[a-zA-Z0-9]", a_text):
        return False, "Question/answer missing content"
    q_clean = re.sub(r'[^a-z0-9_]+', '', q_text.lower())
    a_clean = re.sub(r'[^a-z0-9_]+', '', a_text.lower())
    banned_literals = {"question", "answer", "keypoint_index", "keypointindex"}
    if q_clean in banned_literals or a_clean in banned_literals:
        return False, "Question/answer contains placeholder key"
    
    if q_words > MAX_QUESTION_WORDS:
        return False, f"Question has {q_words} words (max {MAX_QUESTION_WORDS})"
    
    if a_words > MAX_ANSWER_WORDS:
        return False, f"Answer has {a_words} words (max {MAX_ANSWER_WORDS})"
    
    # Reject abstract-only answers (too short)
    if a_words < 12:
        return False, "Answer too short (< 12 words); must be informative"
    
    # Reject meta-references that defer teaching
    if contains_banned_phrase(answer, META_REFERENCE_PATTERNS):
        return False, "Answer must not refer to 'review', 'the material', 'lecture', or 'as discussed'"
    
    # Require mechanism-level content: at least one conditional/causal/process indicator or a number
    has_mechanism = any(re.search(p, a_text.lower()) for p in MECHANISM_INDICATORS)
    has_number = bool(re.search(r'\d+', a_text))
    if not has_mechanism and not has_number:
        return False, "Answer must explain how/why (e.g. 'when', 'because', 'requires', 'uses') or include concrete detail"
    
    if contains_banned_phrase(question, BANNED_QUESTION_PATTERNS):
        return False, "Question contains banned phrase (explain, describe, etc.)"
    
    if contains_banned_phrase(answer, VAGUE_ANSWER_PATTERNS):
        return False, "Answer is too vague"
    
    # Check for generic prompts
    question_lower = q_text.lower().strip()
    if question_lower.startswith(('what do you think', 'in your opinion')):
        return False, "Question is too generic/opinion-based"
    
    if question_lower.startswith(('{', '[')) or answer.lower().strip().startswith(('{', '[')):
        return False, "Question/answer appears to be JSON"

    if answer_echoes_question(question, answer):
        return False, "Answer must explain the concept, not just repeat the question"

    return True, None


def compute_quality_score(question: str, answer: str, keypoint_text: Optional[str] = None) -> float:
    """
    Compute quality score for a flashcard candidate.
    Higher is better.
    """
    score = 0.0
    
    # Good question starters
    question_lower = question.lower().strip()
    good_starters = ['what', 'which', 'when', 'where', 'who', 'how']
    if any(question_lower.startswith(starter) for starter in good_starters):
        if not question_lower.startswith('how do you feel'):
            score += 1.0
    
    # Answer length: reward informative answers (20-45 words optimal)
    a_words = count_words(answer)
    if 20 <= a_words <= 45:
        score += 1.0
    elif 15 <= a_words < 20 or 45 < a_words <= 60:
        score += 0.5
    elif 10 <= a_words < 15:
        score += 0.25
    
    # Causal/conditional language (mechanism-level)
    if any(re.search(p, answer.lower()) for p in MECHANISM_INDICATORS):
        score += 1.0
    
    # Lecture-specific keyword (from keypoint)
    if keypoint_text:
        keypoint_words = set(keypoint_text.lower().split())
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        if keypoint_words.intersection(question_words) or keypoint_words.intersection(answer_words):
            score += 1.0
    
    # Penalties
    if 'various' in answer.lower() or 'several' in answer.lower() or 'it depends' in answer.lower():
        score -= 2.0
    if any(x in answer.lower() for x in ('review', 'material', 'details')):
        score -= 2.0

    # Multi-concept penalty - only if clearly multiple independent targets
    and_count = question.lower().count(' and ')
    comma_count = question.count(',')
    if and_count >= 2 and comma_count >= 1:
        score -= 1.0  # Likely multi-concept; reduced penalty

    return score


def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


def deduplicate_candidates(
    candidates: List[Dict[str, Any]],
    existing_questions: List[str],
    embedding_func,
) -> List[Dict[str, Any]]:
    """
    Remove duplicates from candidates using both exact matching and semantic similarity.
    """
    if not candidates:
        return []
    
    # Normalize existing questions
    existing_normalized = {normalize_text(q): q for q in existing_questions}
    
    # Embed all candidate questions
    candidate_questions = [c.get('question', '') for c in candidates]
    candidate_embeddings = embedding_func(candidate_questions)
    
    # Embed existing questions if any
    existing_embeddings = None
    if existing_questions:
        existing_embeddings = embedding_func(existing_questions)
    
    filtered = []
    seen_normalized = set()
    seen_embeddings = []
    
    for i, candidate in enumerate(candidates):
        question = candidate.get('question', '')
        if not question:
            continue
        
        # Check exact duplicate
        q_normalized = normalize_text(question)
        if q_normalized in existing_normalized or q_normalized in seen_normalized:
            continue
        
        # Check semantic similarity with existing questions
        candidate_emb = candidate_embeddings[i]
        is_duplicate = False
        
        if existing_embeddings:
            for existing_emb in existing_embeddings:
                similarity = compute_cosine_similarity(candidate_emb, existing_emb)
                if similarity > MAX_SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            # Check against already-selected candidates
            for seen_emb in seen_embeddings:
                similarity = compute_cosine_similarity(candidate_emb, seen_emb)
                if similarity > MAX_SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            filtered.append(candidate)
            seen_normalized.add(q_normalized)
            seen_embeddings.append(candidate_emb)
    
    return filtered


def select_final_flashcards(
    candidates: List[Dict[str, Any]],
    target_count: int = FINAL_COUNT,
    max_per_keypoint: int = 2,
) -> List[Dict[str, Any]]:
    """
    Select final flashcards with coverage constraints.
    Ensures max_per_keypoint cards per keypoint_index, spreading across keypoints.
    """
    if len(candidates) <= target_count:
        return candidates
    
    # Group by keypoint_index
    by_keypoint: Dict[int, List[Dict[str, Any]]] = {}
    no_keypoint = []
    
    for candidate in candidates:
        kp_idx = candidate.get('keypoint_index')
        if kp_idx is not None:
            if kp_idx not in by_keypoint:
                by_keypoint[kp_idx] = []
            by_keypoint[kp_idx].append(candidate)
        else:
            no_keypoint.append(candidate)
    
    # Sort each group by quality score
    for kp_idx in by_keypoint:
        by_keypoint[kp_idx].sort(
            key=lambda c: c.get('quality_score', 0.0),
            reverse=True
        )
    
    # Round-robin selection
    selected = []
    keypoint_indices = list(by_keypoint.keys())
    keypoint_positions = {kp_idx: 0 for kp_idx in keypoint_indices}
    
    while len(selected) < target_count and (by_keypoint or no_keypoint):
        # Try to pick from keypoints first
        for kp_idx in keypoint_indices:
            if len(selected) >= target_count:
                break
            
            if kp_idx not in by_keypoint:
                continue
            
            # Check if we've reached max per keypoint
            current_count = sum(1 for s in selected if s.get('keypoint_index') == kp_idx)
            if current_count >= max_per_keypoint:
                continue
            
            pos = keypoint_positions[kp_idx]
            if pos < len(by_keypoint[kp_idx]):
                selected.append(by_keypoint[kp_idx][pos])
                keypoint_positions[kp_idx] += 1
        
        # If we still need more, relax constraint or use no-keypoint cards
        if len(selected) < target_count:
            # Relax to max_per_keypoint + 1 if needed
            if max_per_keypoint >= 2:
                max_per_keypoint = max_per_keypoint + 1
                continue
            
            # Use no-keypoint cards
            if no_keypoint:
                selected.append(no_keypoint.pop(0))
            else:
                break
    
    # Sort by quality score
    selected.sort(key=lambda c: c.get('quality_score', 0.0), reverse=True)
    
    return selected[:target_count]


def _parse_flashcard_candidates(
    response: str,
    key_points: List[str],
    limit: int,
) -> List[Dict[str, Any]]:
    cleaned = re.sub(r'```json\s*', '', response)
    cleaned = re.sub(r'```\s*', '', cleaned)
    cleaned = cleaned.strip()

    parsed: Any = None
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = None

    if parsed is None:
        start = cleaned.find('[')
        end = cleaned.rfind(']')
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                parsed = None

    candidates: List[Dict[str, Any]] = []

    def normalize_pair(text: str) -> Tuple[str, str]:
        text = re.sub(r"^\s*\d+\.\s*", "", text).strip()
        if text.lower().startswith("q:") and "a:" in text.lower():
            parts = re.split(r"\ba:\b", text, maxsplit=1, flags=re.IGNORECASE)
            question = parts[0].replace("Q:", "").strip()
            answer = parts[1].strip() if len(parts) > 1 else ""
            return question, answer
        for splitter in [":", " - ", " — "]:
            if splitter in text:
                left, right = text.split(splitter, 1)
                left = left.strip()
                right = right.strip()
                if left and right:
                    return left, right
        return "", ""

    if isinstance(parsed, list):
        for item in parsed[:limit]:
            if isinstance(item, dict):
                question = item.get("question") or item.get("front") or ""
                answer = item.get("answer") or item.get("back") or ""
                kp_idx = item.get("keypoint_index")
                if question and answer:
                    if kp_idx is not None:
                        try:
                            kp_idx = int(kp_idx)
                            if kp_idx < 1 or kp_idx > len(key_points):
                                kp_idx = None
                        except (ValueError, TypeError):
                            kp_idx = None
                    candidates.append(
                        {
                            "question": str(question).strip(),
                            "answer": str(answer).strip(),
                            "keypoint_index": kp_idx,
                        }
                    )
            elif isinstance(item, str):
                question, answer = normalize_pair(item)
                if question and answer:
                    candidates.append(
                        {"question": question, "answer": answer, "keypoint_index": None}
                    )
        return candidates

    for line in cleaned.splitlines():
        if not line.strip():
            continue
        question, answer = normalize_pair(line)
        if question and answer:
            candidates.append({"question": question, "answer": answer, "keypoint_index": None})
        if len(candidates) >= limit:
            break

    return candidates


def _get_chunks_per_keypoint(
    lecture_id: int,
    key_points: List[str],
    chunks_per_kp: int = 2,
) -> Dict[int, List[str]]:
    """
    Retrieve top relevant chunks for each key point via vector search.
    Returns {keypoint_index_1based: [chunk_text, ...]}.
    """
    if not key_points:
        return {}
    embeddings = embed_texts(key_points)
    result: Dict[int, List[str]] = {}
    for i, (kp, emb) in enumerate(zip(key_points, embeddings)):
        rows = search_similar(emb, top_k=chunks_per_kp, lecture_id=lecture_id)
        texts = [row[0] for row in rows if row[0]]
        if texts:
            result[i + 1] = texts
    return result


def generate_flashcard_candidates(
    key_points: List[str],
    existing_questions: List[str],
    strategy: str = "keypoints_v1",
    candidate_count: int = CANDIDATE_COUNT,
    chunks_per_keypoint: Optional[Dict[int, List[str]]] = None,
) -> List[Dict[str, Any]]:
    """
    Generate flashcard candidates using LLM.
    Returns list of candidate dicts with question, answer, keypoint_index.
    When chunks_per_keypoint is provided, answers are grounded in those excerpts.
    """
    client = DeepSeekClient()
    
    # Format key points for prompt (with optional context excerpts)
    parts = []
    for i, kp in enumerate(key_points):
        idx = i + 1
        parts.append(f"{idx}) {kp}")
        if chunks_per_keypoint and idx in chunks_per_keypoint:
            excerpts = chunks_per_keypoint[idx]
            for j, ex in enumerate(excerpts[:2], 1):
                parts.append(f"   Context {j}: {ex[:500]}{'...' if len(ex) > 500 else ''}")
    key_points_text = "\n".join(parts)
    
    # Format existing questions
    existing_questions_text = ""
    if existing_questions:
        existing_questions_text = "\n\nAvoid repeating these existing questions (semantic duplicates also):\n" + "\n".join(f"- {q}" for q in existing_questions[:10])
    
    # Build prompt based on strategy
    focus_instruction = ""
    if "definitions" in strategy:
        focus_instruction = "\nFocus on definitions and distinctions. Avoid process/step questions unless necessary."
    elif "process" in strategy:
        focus_instruction = "\nFocus on processes and steps. Prefer 'how' questions about procedures."
    
    system_prompt = """You generate study flashcards.

Hard rules:
- Return JSON only. No markdown.
- Generate exactly N flashcard candidates (not final selection).
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
- Avoid vague prompts: "explain in detail", "discuss", "describe fully", "write about".
- Each flashcard must test ONE concept.
- No citations, no page numbers, no timestamps."""
    
    grounding_instruction = ""
    if chunks_per_keypoint:
        grounding_instruction = "\n\nBase each answer STRICTLY on the provided context excerpts. Do not invent details not present in the excerpts."
    
    user_prompt = f"""Create {candidate_count} flashcard CANDIDATES from these key points.

Key points (with context excerpts when provided):
{key_points_text}{existing_questions_text}{grounding_instruction}{focus_instruction}

Return JSON array:
[
  {{"question":"...", "answer":"...", "keypoint_index": 3}},
  ...
]"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    response = client.chat(messages, temperature=0.7).strip()
    candidates = _parse_flashcard_candidates(response, key_points, candidate_count)
    if not candidates:
        fallback_prompt = f"""Create {candidate_count} flashcards using this format only:
Q: <question>
A: <informative answer - 15-60 words, define the concept, explain how/why, use lecture terminology, include at least one concrete detail>

Use these key points:
{key_points_text}

Each answer must: define the concept, explain how it works or why it matters, use specific terms, include a concrete detail. Never say "review the material" or "see the lecture".
Return ONLY Q/A lines, no JSON, no markdown."""
        fallback_messages = [
            {"role": "system", "content": "You create flashcards from key points."},
            {"role": "user", "content": fallback_prompt},
        ]
        response = client.chat(fallback_messages, temperature=0.5).strip()
        candidates = _parse_flashcard_candidates(response, key_points, candidate_count)
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
    client = DeepSeekClient()
    
    existing_questions = [c.get("question", "") for c in already_selected]
    parts = []
    for i, kp in enumerate(key_points):
        idx = i + 1
        parts.append(f"{idx}) {kp}")
        if chunks_per_keypoint and idx in chunks_per_keypoint:
            for j, ex in enumerate(chunks_per_keypoint[idx][:2], 1):
                parts.append(f"   Context {j}: {ex[:500]}{'...' if len(ex) > 500 else ''}")
    key_points_text = "\n".join(parts)
    existing_questions_text = "\n".join(f"- {q}" for q in existing_questions)
    
    system_prompt = """You generate study flashcards.

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
- Avoid vague prompts: "explain in detail", "discuss", "describe fully"."""
    
    user_prompt = f"""You must generate {missing_count} additional flashcards.

Do NOT repeat or paraphrase any of these questions:
{existing_questions_text}

Use these key points:
{key_points_text}
""" + ("\nBase each answer STRICTLY on the provided context excerpts." if chunks_per_keypoint else "") + """

Return JSON array only."""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    response = client.chat(messages, temperature=0.8).strip()
    candidates = _parse_flashcard_candidates(response, key_points, missing_count)
    if not candidates:
        fallback_prompt = f"""Create {missing_count} additional flashcards using this format only:
Q: <question>
A: <informative answer - 15-60 words, define the concept, explain how/why, use lecture terminology, include at least one concrete detail>

Use these key points:
{key_points_text}

Each answer must: define the concept, explain how it works or why it matters, use specific terms, include a concrete detail. Never say "review the material" or "see the lecture".
Return ONLY Q/A lines, no JSON, no markdown."""
        fallback_messages = [
            {"role": "system", "content": "You create flashcards from key points."},
            {"role": "user", "content": fallback_prompt},
        ]
        response = client.chat(fallback_messages, temperature=0.5).strip()
        candidates = _parse_flashcard_candidates(response, key_points, missing_count)
    if not candidates:
        raise ValueError("No flashcards could be parsed from model response")
    return candidates


def _prepare_context_for_chunks(lecture_id: int):
    """Get chunks for lecture (reuse study_materials logic)."""
    chunks = get_chunks_for_lecture(lecture_id, limit=60)
    if not chunks:
        raise ValueError("No chunks found for lecture")
    return chunks


def _generate_flashcards_from_chunks(
    lecture_id: int,
    chunks: List[Tuple[str, Optional[int], Optional[float], Optional[float]]],
    existing_questions: List[str],
) -> List[Dict[str, Any]]:
    """
    Fallback: generate flashcards directly from chunks when key points are missing.
    Selects 5-8 chunks spread across the lecture and creates grounded flashcards.
    """
    if not chunks or len(chunks) < 3:
        raise ValueError("Not enough chunks for flashcard generation")

    # Select up to 8 chunks spread across the lecture
    n = min(8, len(chunks))
    step = max(1, (len(chunks) - 1) // (n - 1)) if n > 1 else 0
    selected_indices = [i * step for i in range(n)] if step > 0 else list(range(n))
    selected_indices = [min(i, len(chunks) - 1) for i in selected_indices]

    context_parts = []
    chunk_refs = []
    for idx in selected_indices:
        text, page, ts_start, ts_end = chunks[idx]
        ref = f"[Page {page}]" if page else (f"[Time {ts_start}-{ts_end}]" if ts_start and ts_end else "[Chunk]")
        context_parts.append(f"{ref} {text.strip()}")
        chunk_refs.append(ref)

    context = "\n\n".join(context_parts)
    client = DeepSeekClient()

    existing_text = ""
    if existing_questions:
        existing_text = "\n\nAvoid repeating: " + "; ".join(existing_questions[:5])

    messages = [
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
                f"Create 5 flashcards from this lecture context. Base each answer strictly on the excerpts. "
                f"Each answer: define the concept, explain how/why, use lecture terms, include a concrete detail (15-60 words). "
                f"Return JSON array: [{{\"question\":\"...\", \"answer\":\"...\", \"source_ref\":\"Page 3\"}}]. "
                f"Use source_ref from context markers (e.g. [Page N] or [Time MM:SS]).{existing_text}\n\nContext:\n{context}\n\nJSON array:"
            ),
        },
    ]
    response = client.chat(messages, temperature=0.5, max_tokens=400).strip()
    response = re.sub(r"^```(?:json)?\s*", "", response)
    response = re.sub(r"\s*```\s*$", "", response).strip()

    candidates = []
    try:
        parsed = json.loads(response)
        if isinstance(parsed, list):
            for i, item in enumerate(parsed[:5]):
                if isinstance(item, dict):
                    q = item.get("question") or item.get("front") or ""
                    a = item.get("answer") or item.get("back") or ""
                    ref = item.get("source_ref") or (chunk_refs[i % len(chunk_refs)] if chunk_refs else None)
                    if q and a:
                        candidates.append({
                            "question": str(q).strip(),
                            "answer": str(a).strip(),
                            "keypoint_index": None,
                            "source_ref": ref,
                        })
    except json.JSONDecodeError:
        pass

    return candidates


def generate_flashcards_v2(
    lecture_id: int,
    user_id: Optional[int] = None,
    strategy: str = "keypoints_v1",
    regenerate: bool = False,
) -> List[Dict[str, Any]]:
    """
    Main flashcard generation pipeline.
    Returns list of 5 validated flashcards.
    Auto-generates key points if missing; falls back to chunks if key points fail.
    """
    # 0. Ensure lecture is ready
    lecture = get_lecture(lecture_id)
    if not lecture:
        raise ValueError(f"Lecture {lecture_id} not found")
    if lecture[4] != "completed":
        raise ValueError(f"Lecture not ready for study materials (status: {lecture[4]})")

    # 1. Fetch or generate keypoints
    key_points = _get_lecture_key_points(lecture_id)
    if not key_points or len(key_points) < 3:
        try:
            _generate_key_points(lecture_id)
            key_points = _get_lecture_key_points(lecture_id)
        except Exception:
            pass

    use_chunks_fallback = not key_points or len(key_points) < 3

    # 2. Fetch prior flashcards if regenerating
    existing_questions = []
    if regenerate:
        existing_questions = get_previous_flashcard_questions(lecture_id, limit_sets=3)

    # 3. Build chunks per key point for grounding (when using key points)
    chunks_per_keypoint: Optional[Dict[int, List[str]]] = None
    if not use_chunks_fallback and key_points:
        try:
            chunks_per_keypoint = _get_chunks_per_keypoint(lecture_id, key_points, chunks_per_kp=2)
        except Exception:
            chunks_per_keypoint = None

    # 4. Generate candidates
    if use_chunks_fallback:
        chunks = _prepare_context_for_chunks(lecture_id)
        candidates = _generate_flashcards_from_chunks(lecture_id, chunks, existing_questions)
        key_points = []  # No key points for selection logic
    else:
        candidates = generate_flashcard_candidates(
            key_points,
            existing_questions,
            strategy=strategy,
            candidate_count=CANDIDATE_COUNT,
            chunks_per_keypoint=chunks_per_keypoint,
        )

    if not candidates:
        raise ValueError("No candidates generated by LLM")
    
    # 4. Validate & filter
    validated = []
    for candidate in candidates:
        is_valid, error = validate_flashcard(
            candidate.get("question", ""),
            candidate.get("answer", ""),
        )
        if is_valid:
            kp_idx = candidate.get("keypoint_index")
            kp_text = key_points[kp_idx - 1] if key_points and kp_idx and 1 <= kp_idx <= len(key_points) else None
            candidate["quality_score"] = compute_quality_score(
                candidate["question"],
                candidate["answer"],
                kp_text,
            )
            validated.append(candidate)
    
    # 5. Deduplicate using embeddings
    # Use simple embedding function for now (can be upgraded to DeepSeek embeddings)
    def embedding_func(texts: List[str]) -> List[List[float]]:
        return embed_texts(texts)
    
    deduplicated = deduplicate_candidates(validated, existing_questions, embedding_func)
    
    # 6. Select best 5 with coverage
    max_per_keypoint = 2 if key_points and len(key_points) >= 5 else 3
    selected = select_final_flashcards(
        deduplicated,
        target_count=FINAL_COUNT,
        max_per_keypoint=max_per_keypoint,
    )
    
    # 7. Fill missing if needed (only when using key points)
    if len(selected) < FINAL_COUNT and key_points:
        missing_count = FINAL_COUNT - len(selected)
        try:
            additional = fill_missing_flashcards(
                key_points,
                selected,
                missing_count,
                chunks_per_keypoint=chunks_per_keypoint,
            )
            # Validate and add
            for candidate in additional:
                is_valid, _ = validate_flashcard(
                    candidate.get("question", ""),
                    candidate.get("answer", ""),
                )
                if is_valid:
                    kp_idx = candidate.get("keypoint_index")
                    kp_text = key_points[kp_idx - 1] if kp_idx and 1 <= kp_idx <= len(key_points) else None
                    candidate["quality_score"] = compute_quality_score(
                        candidate["question"],
                        candidate["answer"],
                        kp_text,
                    )
                    selected.append(candidate)
                    if len(selected) >= FINAL_COUNT:
                        break
        except Exception as e:
            # If fill fails, just return what we have
            pass
    
    # 8. Deterministic fallback from key points (guarantee minimum coverage, only when key points exist)
    if len(selected) < FINAL_COUNT and key_points:
        remaining = FINAL_COUNT - len(selected)
        normalized_existing = {normalize_text(q) for q in existing_questions}
        normalized_existing.update(normalize_text(c.get("question", "")) for c in selected)
        for idx, key_point in enumerate(key_points):
            if remaining <= 0:
                break
            kp_text = (key_point or "").strip().rstrip(".")
            if not kp_text:
                continue
            lower_kp = kp_text.lower()
            if lower_kp.startswith(("how", "what", "why", "when", "where", "who", "which")):
                question = kp_text if kp_text.endswith("?") else f"{kp_text}?"
            else:
                question = f"What is {kp_text}?"
            if normalize_text(question) in normalized_existing:
                continue
            try:
                answer = _expand_keypoint_to_answer(kp_text, question)
                if answer_echoes_question(question, answer):
                    continue  # Skip if LLM still produced echo
            except Exception:
                answer = kp_text  # Last resort
            is_valid, _ = validate_flashcard(question, answer)
            if not is_valid:
                continue
            candidate = {
                "question": question,
                "answer": answer,
                "keypoint_index": idx + 1,
                "quality_score": compute_quality_score(question, answer, kp_text),
            }
            selected.append(candidate)
            normalized_existing.add(normalize_text(question))
            remaining -= 1
    
    # Ensure we return exactly FINAL_COUNT (or as many as possible)
    final = selected[:FINAL_COUNT]
    
    # Add source_keypoint_id and provenance (1-indexed in prompt, 0-indexed in list)
    for card in final:
        kp_idx = card.get("keypoint_index")
        if kp_idx and key_points and 1 <= kp_idx <= len(key_points):
            card["source_keypoint_id"] = kp_idx - 1  # 0-indexed for storage
        # Store source_ref as source_chunk_ids for provenance (chunks fallback)
        if card.get("source_ref"):
            card["source_chunk_ids"] = [card["source_ref"]]

    return final


def _expand_keypoint_to_answer(keypoint: str, question: str) -> str:
    """Use LLM to create an informative answer from a keypoint when fallback is needed."""
    try:
        client = DeepSeekClient()
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
                "content": f"Key point: {keypoint}\n\nQuestion: {question}\n\nProvide a clear, informative answer (15-60 words) that defines the concept and explains how/why it matters:",
            },
        ]
        response = client.chat(messages, temperature=0.3).strip()
        if response and not answer_echoes_question(question, response):
            return response[:500]
        # LLM returned echo, try minimal expansion
        messages[1]["content"] = f"Define {keypoint} in 15-40 words. Include how it works or an example. Never say 'review the material'."
        response = client.chat(messages, temperature=0.2).strip()
        if response and not answer_echoes_question(question, response):
            return response[:400]
    except Exception:
        pass
    # Last resort: raise so caller skips this card (avoids low-quality meta-answers)
    raise ValueError("Cannot generate informative answer from keypoint alone")


def _get_lecture_key_points(lecture_id: int) -> List[str]:
    """Get key points for a lecture."""
    materials = get_lecture_study_materials(lecture_id)
    if not materials:
        return []
    
    key_points = materials.get("key_points", [])
    if isinstance(key_points, str):
        import json
        try:
            key_points = json.loads(key_points)
        except json.JSONDecodeError:
            return []
    
    return key_points if isinstance(key_points, list) else []
