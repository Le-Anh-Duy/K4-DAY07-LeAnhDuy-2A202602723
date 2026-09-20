"""Benchmark cả nhóm: mọi thành viên × mọi chiến lược, trên cùng điều kiện.

    python scripts/run_team_benchmark.py --provider gemini

Artifact NHÓM — kết quả ghi ra `ket_qua_benchmark_nhom.txt`, dùng cho bảng
"So sánh giữa các thành viên" ở REPORT_NHOM mục 2.

Artifact CÁ NHÂN là `bench.py` + `ket_qua_benchmark.txt`: chỉ chạy chiến lược
của riêng mình, in chi tiết top-3 từng câu và phần A/B filter.

Script này chỉ đọc index có sẵn. Dựng index trước bằng:
    python scripts/build_index.py --strategy <st> --provider gemini --package <pkg>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import GOLD_PATH, make_query_embedder, score_query
from src.indexing import INDEX_ROOT, PrecomputedEmbedder, load_chunks, load_vectors
from src.store import EmbeddingStore

# "heading" là chunker tuỳ chỉnh, chỉ Duy viết — người khác sẽ hiện "chưa dựng index".
STRATEGIES = ["fixed", "sentence", "recursive", "heading"]
# Thư mục index → tên hiển thị. `src` là bài của chủ repo, còn lại là bài các bạn nộp.
MEMBERS = [
    ("Duy", "src"),
    ("Duyên", "duyen-chunking"),
    ("Khang", "khang-chunking"),
    ("Thành", "thanh-chunking"),
]


def evaluate(index_dir: Path, gold: dict, query_embedder, top_k: int = 3) -> dict | None:
    if not (index_dir / "vectors.npz").exists():
        return None
    documents = load_chunks(index_dir / "chunks.jsonl")
    by_id, model, dimensions = load_vectors(index_dir / "vectors.npz")

    # Vector tài liệu và vector câu hỏi phải cùng một không gian, nếu không thì
    # điểm số là nhiễu thuần tuý — lỗi này đã thực sự xảy ra một lần.
    # Dò bằng chính câu hỏi gold (đã nằm trong cache) để không tốn thêm quota.
    probe = len(query_embedder(gold["queries"][0]["query"]))
    if probe != dimensions:
        raise SystemExit(
            f"Backend không khớp: {index_dir} là {model} ({dimensions} chiều) "
            f"nhưng embedder cho câu hỏi trả về {probe} chiều. Truyền đúng --provider."
        )

    store = EmbeddingStore(
        collection_name=index_dir.name,
        embedding_fn=PrecomputedEmbedder(
            by_content={doc.content: by_id[doc.id] for doc in documents},
            query_embedder=query_embedder,
        ),
    )
    store.add_documents(documents)

    points = {}
    for item in gold["queries"]:
        results = store.search_with_filter(item["query"], top_k=top_k,
                                           metadata_filter=item.get("metadata_filter"))
        points[item["id"]] = score_query(results, item)[0]
    lengths = [len(doc.content) for doc in documents]
    return {"chunks": len(documents), "avg_length": sum(lengths) / len(lengths),
            "points": points, "total": sum(points.values())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default=None, help="gemini | openai | local | mock")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--out", default="ket_qua_benchmark_nhom.txt")
    args = parser.parse_args()

    load_dotenv(override=False)
    provider = (args.provider or os.getenv("EMBEDDING_PROVIDER", "mock")).strip().lower()
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    query_embedder = make_query_embedder(provider)
    query_ids = [item["id"] for item in gold["queries"]]

    lines = [
        "BENCHMARK NHÓM — ColdBrew, corpus Shopee (7 tài liệu)",
        f"Backend: {getattr(query_embedder, '_backend_name', provider)}",
        "Chấm 2 mức: giao khoảng vùng gold + ngữ cảnh phải chứa chuỗi neo",
        "Cùng corpus, cùng câu hỏi, cùng store — chỉ đổi code chunking của từng người",
        "",
        f"{'Người':7} {'Chiến lược':11} {'chunk':>6} {'dài TB':>7}  "
        + "  ".join(f"{q:>3}" for q in query_ids) + f"  {'Tổng':>6}",
        "-" * 70,
    ]

    best = ("", "", -1)
    for who, package in MEMBERS:
        for strategy in STRATEGIES:
            row = evaluate(INDEX_ROOT / package / strategy, gold, query_embedder, args.top_k)
            if row is None:
                lines.append(f"{who:7} {strategy:11} {'—':>6} {'—':>7}   chưa dựng index")
                continue
            if row["total"] > best[2]:
                best = (who, strategy, row["total"])
            lines.append(
                f"{who:7} {strategy:11} {row['chunks']:6d} {row['avg_length']:7.0f}  "
                + "  ".join(f"{row['points'][q]:>3}" for q in query_ids)
                + f"  {row['total']:>4}/10")

    lines += ["", f"Cao nhất: {best[0]} / {best[1]} = {best[2]}/10"]
    report = "\n".join(lines)
    print(report)
    Path(args.out).write_text(report + "\n", encoding="utf-8")
    print(f"\n→ đã ghi {args.out}")

    if hasattr(query_embedder, "save_cache"):
        query_embedder.save_cache()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
