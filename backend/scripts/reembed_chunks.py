#!/usr/bin/env python3
"""Re-embed existing chunk rows using the configured OpenAI-compatible embedding model."""

from __future__ import annotations

import argparse

from backend.db.postgres import list_chunk_records, update_chunk_embeddings
from backend.services.embeddings import embed_texts


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-embed lecture chunks with the current embedding model.")
    parser.add_argument("--lecture-id", type=int, help="Only re-embed chunks for a single lecture")
    parser.add_argument("--batch-size", type=int, default=64, help="Embedding API batch size")
    args = parser.parse_args()

    records = list_chunk_records(lecture_id=args.lecture_id)
    if not records:
        scope = f" for lecture {args.lecture_id}" if args.lecture_id is not None else ""
        print(f"No chunks found{scope}.")
        return 0

    chunk_ids = [row[0] for row in records]
    texts = [row[2] for row in records]

    print(f"Re-embedding {len(records)} chunks...")
    embeddings = embed_texts(texts, batch_size=args.batch_size)
    update_chunk_embeddings(list(zip(chunk_ids, embeddings)))
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
