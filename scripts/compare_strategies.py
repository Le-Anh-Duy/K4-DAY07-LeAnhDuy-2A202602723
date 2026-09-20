"""So sánh ba chiến lược chunking trên cùng bộ gold, cùng backend.

    python scripts/build_index.py --strategy <mỗi chiến lược>   # phải chạy trước
    python scripts/compare_strategies.py

Chỉ đổi đúng một biến là chiến lược chunking; corpus, bộ câu hỏi, embedding
backend và cách chấm đều giữ nguyên, nên chênh lệch điểm quy hết về chiến lược.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import importlib

from bench import GOLD_PATH, hits_gold, make_query_embedder, score_query
from src.indexing import INDEX_ROOT, PrecomputedEmbedder, load_chunks, load_vectors

STRATEGIES = ["fixed", "sentence", "recursive"]


def evaluate(strategy: str, gold: dict, query_embedder, package: str = "src", top_k: int = 3) -> dict:
    index_dir = INDEX_ROOT / package / strategy
    documents = load_chunks(index_dir / "chunks.jsonl")
    by_id, model, dimensions = load_vectors(index_dir / "vectors.npz")

    # Vector tài liệu và vector câu hỏi phải cùng một không gian, nếu không thì
    # điểm số là nhiễu thuần tuý — đây là lỗi đã thực sự xảy ra một lần.
    probe = len(query_embedder("kiểm tra số chiều"))
    if probe != dimensions:
        raise SystemExit(
            f"Backend không khớp: index '{strategy}' là {model} ({dimensions} chiều) "
            f"nhưng embedder cho câu hỏi trả về {probe} chiều. Truyền đúng --provider."
        )

    EmbeddingStore = importlib.import_module(f"{package}.store").EmbeddingStore
    store = EmbeddingStore(
        collection_name=strategy,
        embedding_fn=PrecomputedEmbedder(
            by_content={doc.content: by_id[doc.id] for doc in documents},
            query_embedder=query_embedder,
        ),
    )
    store.add_documents(documents)

    per_query, total = {}, 0
    for item in gold["queries"]:
        results = store.search_with_filter(item["query"], top_k=top_k,
                                           metadata_filter=item.get("metadata_filter"))
        points, _ = score_query(results, item)
        per_query[item["id"]] = points
        total += points

    lengths = [len(doc.content) for doc in documents]
    return {
        "chunks": len(documents),
        "avg_length": sum(lengths) / len(lengths),
        "max_length": max(lengths),
        "per_query": per_query,
        "total": total,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", default="src", help="package chứa code của người nộp")
    parser.add_argument("--provider", default=None, help="gemini | openai | local | mock")
    args = parser.parse_args()

    load_dotenv(override=False)
    provider = (args.provider or os.getenv("EMBEDDING_PROVIDER", "mock")).strip().lower()
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    query_embedder = make_query_embedder(provider)

    missing = [s for s in STRATEGIES if not (INDEX_ROOT / args.package / s / "vectors.npz").exists()]
    if missing:
        print("Chưa có index cho:", ", ".join(missing))
        for strategy in missing:
            print(f"  python scripts/build_index.py --strategy {strategy} --provider {provider} --package {args.package}")
        return 1

    results = {s: evaluate(s, gold, query_embedder, package=args.package) for s in STRATEGIES}
    query_ids = [item["id"] for item in gold["queries"]]

    print(f"{'Chiến lược':12} {'Chunk':>6} {'Dài TB':>7} {'Dài nhất':>9}  " +
          "  ".join(f"{qid:>3}" for qid in query_ids) + f"  {'Tổng':>6}")
    print("-" * 78)
    for strategy in STRATEGIES:
        row = results[strategy]
        scores = "  ".join(f"{row['per_query'][qid]:>3}" for qid in query_ids)
        print(f"{strategy:12} {row['chunks']:6d} {row['avg_length']:7.0f} {row['max_length']:9d}  "
              f"{scores}  {row['total']:>4}/10")

    best = max(STRATEGIES, key=lambda s: results[s]["total"])
    print(f"\nCao điểm nhất: {best} ({results[best]['total']}/10)")
    for qid in query_ids:
        winners = [s for s in STRATEGIES if results[s]["per_query"][qid] == max(
            results[t]["per_query"][qid] for t in STRATEGIES)]
        best_points = results[winners[0]]["per_query"][qid]
        print(f"  {qid}: {best_points}/2 — {', '.join(winners)}")

    if hasattr(query_embedder, "save_cache"):
        query_embedder.save_cache()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
