from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    NO_CONTEXT = "Không tìm thấy thông tin liên quan trong kho tài liệu."

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def _format_context(self, results: list[dict]) -> str:
        """Đánh số [1] [2] [3] kèm nguồn để câu trả lời truy vết được về đúng chunk."""
        blocks = []
        for index, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})
            source = metadata.get("source_url") or metadata.get("source") or metadata.get("doc_id") or result.get("id")
            blocks.append(f"[{index}] (nguồn: {source})\n{result['content']}")
        return "\n\n".join(blocks)

    def answer(self, question: str, top_k: int = 3, metadata_filter: dict | None = None) -> str:
        results = self.store.search_with_filter(question, top_k=top_k, metadata_filter=metadata_filter)
        if not results:
            # Store rỗng hoặc filter loại hết: báo thẳng, đừng gọi LLM vô ích.
            return self.NO_CONTEXT

        prompt = (
            "Bạn là trợ lý trả lời câu hỏi dựa trên tài liệu được cung cấp.\n"
            "Chỉ dùng thông tin trong phần NGỮ CẢNH dưới đây, tuyệt đối không suy đoán "
            "hay bổ sung kiến thức bên ngoài. Nếu ngữ cảnh không đủ để trả lời, "
            "hãy nói rõ là không tìm thấy thông tin.\n"
            "Mỗi ý trong câu trả lời phải trích dẫn số hiệu đoạn đã dùng, ví dụ [1].\n\n"
            f"NGỮ CẢNH:\n{self._format_context(results)}\n\n"
            f"CÂU HỎI: {question}\n\n"
            "TRẢ LỜI:"
        )
        return self.llm_fn(prompt)
