"""This file parses raw flashcard output from the model.
It converts generated text into structured card objects the app can store or return."""


import json
import re
from typing import Any, Dict, List, Tuple


def parse_flashcard_candidates(
    response: str,
    key_points: List[str],
    limit: int,
) -> List[Dict[str, Any]]:
    """Parse model responses into normalized flashcard candidate dicts."""
    cleaned = re.sub(r"```json\s*", "", response)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()

    parsed: Any = None
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = None

    if parsed is None:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(cleaned[start : end + 1])
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
