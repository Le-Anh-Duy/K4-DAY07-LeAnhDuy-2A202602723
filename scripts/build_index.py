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
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import GeminiEmbedder, LocalEmbedder, OpenAIEmbedder, _mock_embed
from src.indexing import INDEX_ROOT, chunk_corpus, save_chunks, save_vectors

STRATEGIES = {
    "fixed": lambda: FixedSizeChunker(chunk_size=800, overlap=80),
    "sentence": lambda: SentenceChunker(max_sentences_per_chunk=3, max_chars=1000),
    "recursive": lambda: RecursiveChunker(chunk_size=800),
}


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
    args = parser.parse_args()

    load_dotenv(override=False)
    provider = (args.provider or os.getenv("EMBEDDING_PROVIDER", "mock")).strip().lower()

    documents = chunk_corpus(STRATEGIES[args.strategy]())
    out_dir = INDEX_ROOT / args.strategy
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
