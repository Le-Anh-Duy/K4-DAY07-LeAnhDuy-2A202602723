"""Bước 1 của pipeline: chunk corpus rồi embed, lưu cả hai xuống đĩa.

    python scripts/build_index.py --strategy recursive
    python scripts/build_index.py --strategy sentence --provider mock

Sinh ra:
    data/index/<strategy>/chunks.jsonl   — từng chunk kèm metadata, xem bằng mắt được
    data/index/<strategy>/vectors.npz    — ma trận embedding khớp theo chunk id

Chạy `bench.py` sau đó chỉ nạp index này, không chunk lại và không gọi API cho
tài liệu nữa.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.embeddings import GeminiEmbedder, LocalEmbedder, OpenAIEmbedder, _mock_embed
from src.indexing import INDEX_ROOT, chunk_corpus, save_chunks, save_vectors


def load_chunking_module(package: str):
    """Nạp module chunking của người nộp bài.

    Nhận cả tên package (`src`, `src_khang`) lẫn đường dẫn tới file `.py` rời —
    bài nộp của các bạn là file đơn, tên lại có dấu gạch nối nên không import
    theo kiểu module thông thường được.
    """
    path = Path(package)
    if path.suffix == ".py":
        spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return importlib.import_module(f"{package}.chunking")


def make_chunker(package: str, strategy: str):
    """Lấy chunker từ code của người nộp bài — mỗi thành viên tự viết phần của mình.

    SentenceChunker của mỗi người có chữ ký khác nhau (max_chars là thứ tôi tự
    thêm), nên thử tham số đầy đủ trước rồi lùi về tham số chuẩn của lab.
    """
    chunking = load_chunking_module(package)
    if strategy == "fixed":
        return chunking.FixedSizeChunker(chunk_size=800, overlap=80)
    if strategy == "recursive":
        return chunking.RecursiveChunker(chunk_size=800)
    try:
        return chunking.SentenceChunker(max_sentences_per_chunk=3, max_chars=1000)
    except TypeError:
        return chunking.SentenceChunker(max_sentences_per_chunk=3)


STRATEGIES = ["fixed", "sentence", "recursive"]


def make_embedder(provider: str):
    if provider == "gemini":
        return GeminiEmbedder()
    if provider == "openai":
        return OpenAIEmbedder()
    if provider == "local":
        return LocalEmbedder()
    return _mock_embed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=STRATEGIES, default="recursive")
    parser.add_argument("--provider", default=None, help="gemini | openai | local | mock")
    parser.add_argument("--package", default="src", help="package chứa code của người nộp, vd src_khang")
    args = parser.parse_args()

    load_dotenv(override=False)
    provider = (args.provider or os.getenv("EMBEDDING_PROVIDER", "mock")).strip().lower()

    documents = chunk_corpus(make_chunker(args.package, args.strategy))
    out_dir = INDEX_ROOT / Path(args.package).stem / args.strategy
    count = save_chunks(out_dir / "chunks.jsonl", documents)
    print(f"[1/2] chunk : {count} chunk → {out_dir / 'chunks.jsonl'}")

    embedder = make_embedder(provider)
    model = getattr(embedder, "model_name", "mock")
    dimensions = getattr(embedder, "dimensions", 64)
    print(f"[2/2] embed : {getattr(embedder, '_backend_name', provider)}")

    if hasattr(embedder, "warm"):
        embedder.warm([doc.content for doc in documents], task_type="RETRIEVAL_DOCUMENT")
    embed_document = getattr(embedder, "embed_document", embedder)
    vectors = [embed_document(doc.content) for doc in documents]
    if hasattr(embedder, "save_cache"):
        embedder.save_cache()

    saved = save_vectors(out_dir / "vectors.npz", [doc.id for doc in documents], vectors, model, dimensions)
    print(f"        {saved} vector ({dimensions}d) → {out_dir / 'vectors.npz'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
