from __future__ import annotations

from typing import Any, Callable

from .chunking import compute_similarity
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    An in-memory vector store for text chunks.

    Every document is embedded once on insert and kept as a record holding its
    id, content, a copy of its metadata, and the embedding. Search embeds the
    query and ranks records by cosine similarity.

    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._collection_name = collection_name
        self._embedding_fn = embedding_fn or _mock_embed
        # Backend bất đối xứng (Gemini task_type, prefix kiểu E5) cần biết đang
        # embed tài liệu hay câu hỏi. Backend nào không phân biệt thì dùng chung.
        self._embed_document = getattr(self._embedding_fn, "embed_document", self._embedding_fn)
        self._records: list[dict[str, Any]] = []

    def add_documents(self, docs: list[Document]) -> None:
        """Embed each document's content and store it. One Document = one record."""
        for doc in docs:
            # Copy chứ không dùng thẳng dict của người gọi — sửa metadata sau khi
            # nạp thì không được phép đổi nội dung đã lưu trong store.
            metadata = dict(doc.metadata or {})
            # delete_document tìm theo metadata['doc_id']. Khi nạp cả file làm một
            # Document thì metadata rỗng, nên lấy chính doc.id làm mặc định.
            metadata.setdefault("doc_id", doc.id)
            self._records.append(
                {
                    "id": doc.id,
                    "content": doc.content,
                    "metadata": metadata,
                    "embedding": self._embed_document(doc.content),
                }
            )

    def _rank(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        """Xếp hạng một tập record bất kỳ theo độ tương tự với query.

        search() và search_with_filter() chỉ khác nhau ở tập ứng viên đưa vào, nên
        cho cả hai đi qua đây thì kết quả không thể lệch nhau.
        """
        query_vector = self._embedding_fn(query)
        scored = [
            {
                "id": record["id"],
                "content": record["content"],
                "metadata": record["metadata"],
                "score": compute_similarity(query_vector, record["embedding"]),
            }
            for record in records
        ]
        # Bỏ 'embedding' khỏi kết quả: vector vài trăm chiều làm bẩn output terminal.
        scored.sort(key=lambda record: record["score"], reverse=True)
        return scored[:top_k]

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Find the top_k most similar documents to query."""
        return self._rank(query, self._records, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._records)

    def search_with_filter(
        self,
        query: str,
        top_k: int = 3,
        metadata_filter: dict | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search with optional metadata pre-filtering.

        Lọc TRƯỚC rồi mới xếp hạng. Làm ngược lại — lấy top_k rồi mới loại cái
        không khớp — có thể trả về 0 kết quả dù store vẫn còn tài liệu hợp lệ,
        vì k chỗ đã bị tài liệu sai chiếm hết.
        """
        candidates = self._records
        if metadata_filter:
            candidates = [
                record
                for record in self._records
                if all(record["metadata"].get(key) == value for key, value in metadata_filter.items())
            ]
        return self._rank(query, candidates, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """Remove all chunks belonging to a document. True nếu có xoá được gì."""
        size_before = len(self._records)
        self._records = [r for r in self._records if r["metadata"].get("doc_id") != doc_id]
        return len(self._records) < size_before
