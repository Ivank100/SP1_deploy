"""This file generates key-point study materials from lecture content.
It turns lecture text into concise takeaways students can review quickly."""


import json
import re
from typing import List

from ...clients.openai import OpenAIClient
from ...db.postgres import save_lecture_key_points
from .shared import (
    ensure_ready_lecture,
    fallback_keypoints_repair,
    is_valid_keypoint,
    prepare_context,
)


def generate_key_points(lecture_id: int) -> List[str]:
    ensure_ready_lecture(lecture_id)
    context, _chunks = prepare_context(lecture_id)
    client = OpenAIClient()
    messages = [
        {
            "role": "system",
            "content": "You extract concise noun-phrase key points from lecture content.",
        },
        {
            "role": "user",
            "content": (
                "Output ONLY a JSON array of strings.\n"
                "Return 5-8 key points.\n"
                "Each key point must be a noun phrase (no full sentences).\n"
                "Up to 10 words each; allow structured phrases like 'Safe state condition in Banker's algorithm'.\n"
                "No ending period. No verbs like includes / involves / manages.\n"
                "No punctuation except / and -.\n"
                "Use lecture terminology only. Preserve conceptual anchors (e.g. 'Deadlock necessary conditions', 'Reusable vs consumable resources').\n\n"
                f"Context:\n{context}\n\nJSON array:"
            ),
        },
    ]
    response = client.chat(messages, max_tokens=303, temperature=0.3).strip()
    response = re.sub(r"^```(?:json)?\s*", "", response)
    response = re.sub(r"\s*```\s*$", "", response).strip()

    try:
        parsed = json.loads(response)
        if isinstance(parsed, list):
            key_points = [str(item).strip() for item in parsed if is_valid_keypoint(str(item))]
            key_points = key_points[:8]
        else:
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        key_points = [
            line.strip("-• ").strip("[],")
            for line in response.splitlines()
            if line.strip() and is_valid_keypoint(line.strip("-• "))
        ][:8]

    if key_points:
        cleaned_points = []
        for point in key_points:
            cleaned = re.sub(r"^\s*\d+\.\s*", "", point).strip()
            cleaned = re.sub(r"[.]$", "", cleaned)
            lower = cleaned.lower()
            if re.match(r"^\s*(includes|involves|manages|covers|describes)\b", lower):
                continue
            words = cleaned.split()
            if len(words) > 10:
                cleaned = " ".join(words[:10])
            if cleaned and is_valid_keypoint(cleaned):
                cleaned_points.append(cleaned)
        key_points = cleaned_points[:8]

    if not key_points:
        key_points = fallback_keypoints_repair(context)
    if not key_points:
        raise ValueError("Could not extract key points from model response")
    save_lecture_key_points(lecture_id, key_points)
    return key_points
