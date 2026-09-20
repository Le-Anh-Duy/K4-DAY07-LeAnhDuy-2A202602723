from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


import re

class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Handled edge cases:
    - Decimals & version numbers: 1.5, 3.14, v2.0
    - Ellipsis: '...' or '…'
    - Common abbreviations: TS., PGS., ThS., BS., v.v., e.g., i.e., Mr., Dr.
    - URLs & Emails: example.com, test@domain.vn
    - Closing quotes/brackets after punctuation: ." or !)
    - Multi-line breaks & extra whitespace
    """

    # Danh sách các từ viết tắt phổ biến (Việt + Anh)
    ABBREVIATIONS = [
        r"TS", r"ThS", r"PGS", r"GS", r"BS", r"Thầy",
        r"Mr", r"Mrs", r"Ms", r"Dr", r"Prof",
        r"v\.v", r"etc", r"e\.g", r"i\.e", r"tp", r"TP"
    ]

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)
        self._build_regex()

    def _build_regex(self) -> None:
        abbrev_pattern = "|".join(self.ABBREVIATIONS)

        # Regex tách câu:
        # 1. (?<!\b(?:...)\.)  : Không tách nếu đứng sau từ viết tắt
        # 2. (?<!\d)           : Không tách sau số (tránh 1.5, 2.0)
        # 3. (?<!\.\.)         : Không tách nếu là dấu 3 chấm (...)
        # 4. ([.!?…]+[\"\')\]]*): Bắt dấu kết thúc câu kèm dấu ngoặc kép/đơn đi liền sau
        # 5. (?!\S)            : Phía sau phải là khoảng trắng hoặc hết dòng (tránh URL/domain)
        # 6. \s+               : Nuốt khoảng trắng kế tiếp
        self._pattern = re.compile(
            rf"""
            (?<!\b(?:{abbrev_pattern})) # Bỏ qua viết tắt
            (?<!\d)                     # Bỏ qua số thập phân
            (?<!\.\.)                   # Bỏ qua ellipsis (...)
            ([.!?…]+[\"\')\]]*)         # Dấu kết thúc + đóng ngoặc (nếu có)
            (?!\S)                      # Tránh URL hoặc tên file (như domain.com)
            \s+                         # Khoảng trắng phân tách
            """,
            re.VERBOSE | re.IGNORECASE,
        )

    def _split_into_sentences(self, text: str) -> list[str]:
        # Dùng capture group ([.!?…]+...) để giữ lại dấu câu khi split
        parts = self._pattern.split(text)
        sentences = []
        
        # parts sẽ có dạng: [đoạn 1, dấu câu 1, đoạn 2, dấu câu 2, ..., đoạn cuối]
        i = 0
        while i < len(parts):
            sentence = parts[i].strip()
            # Nếu có dấu câu đi kèm ở phần tử tiếp theo, nối lại
            if i + 1 < len(parts):
                punct = parts[i + 1].strip()
                sentence = f"{sentence}{punct}".strip()
                i += 2
            else:
                i += 1
            
            if sentence:
                sentences.append(sentence)

        return sentences

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        # Chuẩn hóa khoảng trắng thừa & xuống dòng rải rác
        cleaned_text = re.sub(r"[ \t]+", " ", text.strip())

        sentences = self._split_into_sentences(cleaned_text)
        size = self.max_sentences_per_chunk

        chunks = []
        for i in range(0, len(sentences), size):
            chunk_content = " ".join(sentences[i : i + size]).strip()
            if chunk_content:
                chunks.append(chunk_content)

        return chunks

class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text.strip():
            return []
        return self._split(text, self.separators)

    def _hard_cut(self, text: str) -> list[str]:
        return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        current_text = current_text.strip()
        if not current_text:
            return []
        if len(current_text) <= self.chunk_size:
            return [current_text]

        separator = remaining_separators[0] if remaining_separators else ""
        if separator == "":
            return self._hard_cut(current_text)

        rest = remaining_separators[1:]
        chunks: list[str] = []
        buffer = ""
        for piece in current_text.split(separator):
            candidate = piece if not buffer else buffer + separator + piece
            if len(candidate) <= self.chunk_size:
                buffer = candidate
                continue
            if buffer:
                chunks.append(buffer)
                buffer = ""
            # Still too big on its own: drop to the next, finer separator.
            if len(piece) > self.chunk_size:
                chunks.extend(self._split(piece, rest))
            else:
                buffer = piece
        if buffer:
            chunks.append(buffer)
        return [c.strip() for c in chunks if c.strip()]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    norm_a = math.sqrt(_dot(vec_a, vec_a))
    norm_b = math.sqrt(_dot(vec_b, vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=chunk_size // 10),
            "by_sentences": SentenceChunker(),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }
        results = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            total = sum(len(c) for c in chunks)
            results[name] = {
                "count": len(chunks),
                "avg_length": total / len(chunks) if chunks else 0.0,
                "chunks": chunks,
            }
        return results
