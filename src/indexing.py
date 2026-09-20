"""Các bước của pipeline dữ liệu, tách rời để lưu được kết quả trung gian.

    corpus .md  →  chunk_corpus()  →  chunks.jsonl  →  embed  →  vectors.npz

Tách ra vì ba lý do: chunk phải xem lại được bằng mắt khi phân tích lỗi, mỗi
chiến lược cần một bộ chunk riêng để so sánh công bằng, và embedding gọi API
mất tiền lẫn thời gian chờ hạn mức nên không được tính lại mỗi lần chạy.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import Document

DATA_DIR = Path("data/shopee-ecommerce")
INDEX_ROOT = Path("data/index")


def split_frontmatter(raw: str) -> tuple[dict, str]:
    """Tách YAML frontmatter thành metadata và phần thân. Offset bám vào phần thân."""
    _, front, body = raw.split("---", 2)
    metadata = {}
    for line in front.strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')
    return metadata, body.lstrip("\n")


def locate(body: str, chunk: str, cursor: int) -> tuple[int, int]:
    """Tìm vị trí của một chunk trong tài liệu gốc, trả về nửa khoảng [start, end).

    Không phải chunker nào cũng trả về chuỗi khớp nguyên văn với tài liệu:
    SentenceChunker gộp khoảng trắng, còn HeadingChunker **ghép thêm tiêu đề vào
    đầu** mỗi mảnh con. Vì vậy khớp nguyên văn trước, không được thì dò theo các
    đoạn đuôi ngắn dần — đuôi mới là phần văn bản thật, phần đầu có thể là tiêu
    đề được gắn vào từ chỗ khác.
    """
    start = body.find(chunk, cursor)
    if start >= 0:
        return start, start + len(chunk)

    for length in (240, 120, 60, 30):
        if len(chunk) <= length:
            continue
        tail = chunk[-length:]
        position = body.find(tail, cursor)
        if position >= 0:
            return position, position + len(tail)

    head = body.find(chunk[:40], cursor)
    if head >= 0:
        return head, head + len(chunk)
    return cursor, cursor + len(chunk)


def chunk_corpus(chunker, data_dir: Path = DATA_DIR) -> list[Document]:
    """Chunk toàn corpus. Mỗi chunk thành một Document id = doc_id_start_end."""
    documents: list[Document] = []
    for path in sorted(data_dir.glob("*.md")):
        metadata, body = split_frontmatter(path.read_text(encoding="utf-8"))
        cursor = 0
        for chunk in chunker.chunk(body):
            start, end = locate(body, chunk, cursor)
            cursor = max(cursor, start + 1)
            documents.append(
                Document(
                    id=f"{path.stem}_{start}_{end}",
                    content=chunk,
                    # Trải metadata frontmatter vào MỌI chunk, nếu không thì
                    # search_with_filter không có gì để lọc.
                    metadata={**metadata, "doc_id": path.stem, "start": start, "end": end},
                )
            )
    return documents


def save_chunks(path: Path, documents: list[Document]) -> int:
    """Ghi chunks.jsonl — mỗi dòng một chunk, đọc bằng mắt được khi phân tích lỗi."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for doc in documents:
            handle.write(json.dumps({"id": doc.id, "content": doc.content, "metadata": doc.metadata},
                                    ensure_ascii=False) + "\n")
    return len(documents)


def load_chunks(path: Path) -> list[Document]:
    with path.open(encoding="utf-8") as handle:
        return [Document(**json.loads(line)) for line in handle if line.strip()]


def save_vectors(path: Path, ids: list[str], vectors: list[list[float]], model: str, dimensions: int) -> int:
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        ids=np.array(ids),
        vectors=np.array(vectors, dtype=np.float32),
        model=np.array(model),
        dimensions=np.array(dimensions),
    )
    return len(ids)


def load_vectors(path: Path) -> tuple[dict[str, list[float]], str, int]:
    import numpy as np

    data = np.load(path, allow_pickle=False)
    by_id = {str(chunk_id): vector.tolist() for chunk_id, vector in zip(data["ids"], data["vectors"])}
    return by_id, str(data["model"]), int(data["dimensions"])


class PrecomputedEmbedder:
    """Dùng vector đã lưu cho tài liệu; câu hỏi thì vẫn embed thật.

    Nhờ lớp này mà EmbeddingStore không cần biết gì về index trên đĩa.
    """

    def __init__(self, by_content: dict[str, list[float]], query_embedder=None, backend_name: str = "precomputed"):
        self._by_content = by_content
        self._query_embedder = query_embedder
        self._backend_name = backend_name

    def embed_document(self, text: str) -> list[float]:
        return self._by_content[text]

    def __call__(self, text: str) -> list[float]:
        if self._query_embedder is None:
            raise RuntimeError("Cần một embedder thật để embed câu hỏi")
        return self._query_embedder(text)
