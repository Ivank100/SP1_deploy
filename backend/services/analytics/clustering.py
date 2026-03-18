"""This file implements analytics logic for clustering insights.
It turns raw lecture or question data into summaries the API can return."""


from collections import defaultdict
from typing import Any, Dict, List

from ..embeddings import embed_texts


def cluster_questions(
    questions: List[str], n_clusters: int = 5
) -> List[Dict[str, Any]]:
    if not questions or len(questions) < n_clusters:
        return []

    try:
        from sklearn.cluster import KMeans
        import numpy as np
    except ImportError:
        return _simple_cluster_fallback(questions)

    embeddings = embed_texts(questions)
    x_values = np.array(embeddings)

    kmeans = KMeans(n_clusters=min(n_clusters, len(questions)), random_state=42, n_init=10)
    labels = kmeans.fit_predict(x_values)

    clusters: Dict[int, List[str]] = defaultdict(list)
    for idx, label in enumerate(labels):
        clusters[label].append(questions[idx])

    result = []
    for cluster_id, cluster_questions_list in clusters.items():
        if not cluster_questions_list:
            continue
        result.append(
            {
                "cluster_id": cluster_id,
                "count": len(cluster_questions_list),
                "questions": cluster_questions_list[:10],
                "representative_question": cluster_questions_list[0],
            }
        )

    return sorted(result, key=lambda item: item["count"], reverse=True)


def _simple_cluster_fallback(questions: List[str]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[str]] = defaultdict(list)
    for question in questions:
        first_word = question.split()[0].lower() if question.split() else "other"
        groups[first_word].append(question)

    return [
        {
            "cluster_id": idx,
            "count": len(grouped_questions),
            "questions": grouped_questions[:10],
            "representative_question": grouped_questions[0] if grouped_questions else "",
        }
        for idx, (_, grouped_questions) in enumerate(groups.items())
    ]
