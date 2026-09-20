"""Bước 2 của pipeline: chấm điểm truy xuất trên bộ gold của nhóm ColdBrew.

    python scripts/build_index.py --strategy recursive    # phải chạy trước
    python bench.py --strategy recursive

Chỉ nạp index có sẵn — không chunk lại, không embed lại tài liệu. Chỉ câu hỏi
mới cần gọi API (và cũng đã được cache).

Chấm hai mức theo CP6:
    - Mức tài liệu: chunk truy xuất được có giao với vùng gold [start, end) không.
    - Mức nội dung: ngữ cảnh top-k có thật sự chứa chuỗi `anchor` không.
Chỉ chấm mức tài liệu sẽ thổi phồng kết quả — một chiến lược có thể chiếm cả
top-3 bằng đúng tài liệu gold mà không chunk nào chứa câu trả lời.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from src.embeddings import GeminiEmbedder, LocalEmbedder, OpenAIEmbedder, _mock_embed
from src.indexing import INDEX_ROOT, PrecomputedEmbedder, load_chunks, load_vectors
from src.store import EmbeddingStore

GOLD_PATH = Path("data/shopee-ecommerce/gold.json")


def make_query_embedder(provider: str):
    if provider == "gemini":
        return GeminiEmbedder()
    if provider == "openai":
        return OpenAIEmbedder()
    if provider == "local":
        return LocalEmbedder()
    return _mock_embed


def hits_gold(result: dict, gold_spans: list[dict]) -> bool:
    """Giao khoảng: chunk [s,e) trúng khi s < gold_end và e > gold_start."""
    for span in gold_spans:
        if result["metadata"]["doc_id"] != span["doc_id"]:
            continue
        if result["metadata"]["start"] < span["end"] and result["metadata"]["end"] > span["start"]:
            return True
    return False


def score_query(results: list[dict], item: dict) -> tuple[int, str]:
    """2đ nếu gold ở top-1 và ngữ cảnh chứa anchor; 1đ nếu gold ở top-2/3; 0 nếu vắng."""
    ranks = [i for i, r in enumerate(results, start=1) if hits_gold(r, item["gold_spans"])]
    has_anchor = any(item["anchor"] in r["content"] for r in results)
    if not ranks:
        return 0, "gold vắng khỏi top-3"
    if ranks[0] == 1 and has_anchor:
        return 2, "gold ở top-1, ngữ cảnh chứa anchor"
    if has_anchor:
        return 1, f"gold ở top-{ranks[0]}, ngữ cảnh chứa anchor"
    return 1, f"gold ở top-{ranks[0]} nhưng ngữ cảnh THIẾU anchor"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="recursive")
    parser.add_argument("--provider", default=None, help="gemini | openai | local | mock")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    load_dotenv(override=False)
    provider = (args.provider or os.getenv("EMBEDDING_PROVIDER", "mock")).strip().lower()

    index_dir = INDEX_ROOT / args.strategy
    if not (index_dir / "vectors.npz").exists():
        print(f"Chưa có index ở {index_dir}. Chạy trước:")
        print(f"  python scripts/build_index.py --strategy {args.strategy} --provider {provider}")
        return 1

    documents = load_chunks(index_dir / "chunks.jsonl")
    by_id, model, dimensions = load_vectors(index_dir / "vectors.npz")
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))

    embedder = PrecomputedEmbedder(
        by_content={doc.content: by_id[doc.id] for doc in documents},
        query_embedder=make_query_embedder(provider),
        backend_name=f"{model} ({dimensions}d, index có sẵn)",
    )

    print(f"Chiến lược : {args.strategy}")
    print(f"Index      : {len(documents)} chunk từ {index_dir}")
    print(f"Backend    : {embedder._backend_name}\n")

    store = EmbeddingStore(collection_name="shopee", embedding_fn=embedder)
    store.add_documents(documents)

    total = 0
    for item in gold["queries"]:
        metadata_filter = item.get("metadata_filter")
        results = store.search_with_filter(item["query"], top_k=args.top_k, metadata_filter=metadata_filter)
        points, note = score_query(results, item)
        total += points

        print(f"{item['id']} [{item['question_type']}] {item['query']}")
        print(f"   filter: {metadata_filter or '—'}   →  {points}/2 điểm  ({note})")
        for rank, result in enumerate(results, start=1):
            mark = "✓" if hits_gold(result, item["gold_spans"]) else " "
            preview = result["content"][:70].replace("\n", " ")
            print(f"   {mark} {rank}. {result['score']:.3f}  {result['id']:22} {preview}...")
        print()

    print(f"TỔNG: {total}/{2 * len(gold['queries'])} điểm")

    # A/B bắt buộc ở CP6: chạy câu cần filter hai lần để chứng minh nó thật sự cần.
    ab = next((q for q in gold["queries"] if q.get("metadata_filter")), None)
    if ab:
        print(f"\n=== A/B cho {ab['id']} (câu cần lọc metadata) ===")
        for label, metadata_filter in [("CÓ filter", ab["metadata_filter"]), ("KHÔNG filter", None)]:
            results = store.search_with_filter(ab["query"], top_k=args.top_k, metadata_filter=metadata_filter)
            points, note = score_query(results, ab)
            print(f"{label:13} {points}/2 — {note}")
            for rank, result in enumerate(results, start=1):
                print(f"   {rank}. {result['score']:.3f}  {result['metadata']['doc_id']} "
                      f"(audience={result['metadata'].get('audience')})  {result['id']}")

    query_embedder = embedder._query_embedder
    if hasattr(query_embedder, "save_cache"):
        query_embedder.save_cache()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
