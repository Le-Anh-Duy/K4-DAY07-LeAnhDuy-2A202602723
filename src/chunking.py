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


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    A sentence ends at ".", "!", "?" or "…" (plus any closing quote/bracket)
    followed by whitespace. That trailing-whitespace requirement alone already
    rules out decimals (1.5), versions (v2.0), URLs and emails, because the dot
    inside them is never followed by a space.

    Two vetoes are applied on top, both driven by the token in front of the dot:
        - abbreviations: TS., ThS., Mr., v.v., e.g. ...
        - list/clause numbering: "1.", "3.1.", "a.", "i." — very common in the
          Shopee policy corpus, where a break there would strip the numbering
          off the clause it labels and leave a 3-character fragment behind.

    Known limitation: an abbreviation outside ABBREVIATIONS still splits wrongly.
    """

    # Không có dấu chấm cuối; so khớp không phân biệt hoa thường.
    ABBREVIATIONS = {
        "ts", "ths", "pgs", "gs", "bs", "cn", "kts",
        "mr", "mrs", "ms", "dr", "prof", "st",
        "v.v", "vv", "etc", "e.g", "i.e", "tp", "q", "p",
    }

    # Dấu kết thúc câu + dấu đóng đi liền, và bắt buộc có khoảng trắng phía sau.
    _BREAK = re.compile(r"[.!?…]+[\"'’”»)\]]*(?=\s|$)")
    # Token đứng ngay trước dấu chấm (phần không phải khoảng trắng).
    _TOKEN = re.compile(r"\S+$")
    # Đánh số mục: 1 / 3.1 / 10.2.3
    _NUMBERING = re.compile(r"^\d+(?:\.\d+)*$")
    # Đầu mục liệt kê ngay sau dấu chấm: "a.", "b)", "iv.", "3.", "3.1."
    _LIST_MARKER = re.compile(r"^(?:[a-z]{1,2}|[ivx]{1,4}|\d+(?:\.\d+)*)[.)]", re.IGNORECASE)

    def __init__(self, max_sentences_per_chunk: int = 3, max_chars: int = 1000) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)
        self.max_chars = max_chars

    def _is_false_break(self, text: str, punct_start: int, punct_end: int) -> bool:
        """True nếu dấu chấm tại vị trí này không thực sự kết thúc câu."""
        match = self._TOKEN.search(text, 0, punct_start)
        raw = match.group().rstrip(".!?…") if match else ""
        token = raw.lower()
        if token:
            if token in self.ABBREVIATIONS:
                return True
            if self._NUMBERING.match(token):
                return True
            # Một chữ cái đơn: viết tắt tên riêng ("A. Nguyễn") hoặc mục a./b./i.
            if len(token) == 1 and token.isalpha():
                return True
            # Số La Mã viết hoa đầu mục ("XII."). Bắt buộc viết hoa để không
            # nhận nhầm các từ tiếng Việt như "vi", "mi".
            if len(raw) > 1 and raw.isupper() and set(raw) <= set("IVXLCDM"):
                return True

        # Câu mới phải mở đầu bằng chữ hoa. Chữ thường phía sau nghĩa là dấu chấm
        # nằm giữa câu — điển hình là "nói... rồi im lặng" hay 'hỏi "?" rồi đi'.
        # Ngoại lệ: đầu mục liệt kê ("a.", "iv.") cũng viết thường nhưng là mục mới.
        nxt = text[punct_end:].lstrip()
        if nxt and nxt[0].islower() and not self._LIST_MARKER.match(nxt):
            return True
        return False

    def _split_into_sentences(self, text: str) -> list[str]:
        sentences: list[str] = []
        cursor = 0
        for match in self._BREAK.finditer(text):
            if self._is_false_break(text, match.start(), match.end()):
                continue
            sentence = text[cursor : match.end()].strip()
            if sentence:
                sentences.append(sentence)
            cursor = match.end()
        tail = text[cursor:].strip()
        if tail:
            sentences.append(tail)
        return sentences

    def chunk(self, text: str) -> list[str]:
        if not text.strip():
            return []

        # Gộp khoảng trắng ngang thừa; giữ nguyên xuống dòng để không dính chữ.
        cleaned = re.sub(r"[ \t\r\f\v ]+", " ", text.strip())

        sentences = self._split_into_sentences(cleaned)
        size = self.max_sentences_per_chunk

        chunks: list[str] = []
        for i in range(0, len(sentences), size):
            group = " ".join(sentences[i : i + size])
            if not group:
                continue
            # Văn bản quy định liệt kê bằng dấu chấm phẩy — "(m) ...; (n) ...;" —
            # và bảng phí thì không có dấu kết câu nào, nên một "câu" có thể dài
            # hơn 3000 ký tự. Hạ xuống RecursiveChunker cho những khối như vậy.
            if self.max_chars and len(group) > self.max_chars:
                chunks.extend(RecursiveChunker(chunk_size=self.max_chars).chunk(group))
            else:
                chunks.append(group)
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
            if len(piece) > self.chunk_size:
                # Đệ quy trên cả candidate chứ không riêng piece: buffer lúc này
                # thường là đầu mục ("m.", "i.") — xả riêng thì thành chunk 1 ký tự
                # và mảnh đi sau mất luôn nhãn của nó.
                chunks.extend(self._split(candidate, rest))
                buffer = ""
            else:
                if buffer:
                    chunks.append(buffer)
                buffer = piece
        if buffer:
            chunks.append(buffer)
        return [c.strip() for c in chunks if c.strip()]


class HeadingChunker:
    """
    Chunk theo mục của văn bản quy định: cắt trước mỗi dòng tiêu đề, mỗi mục
    thành một chunk, mục nào dài quá thì hạ xuống RecursiveChunker.

    Người soạn văn bản đã chia sẵn nội dung thành các mục có nghĩa trọn vẹn
    ("A. PHẠM VI VÀ ĐỐI TƯỢNG ÁP DỤNG", "3. ĐIỀU KIỆN YÊU CẦU TRẢ HÀNG"), nên
    bám theo đó tốt hơn là tự đoán ranh giới.

    Chi tiết quan trọng nhất: khi phải cắt nhỏ một mục dài, **gắn lại tiêu đề
    vào từng mảnh con**. Không có nó, mảnh thứ hai trở đi mất ngữ cảnh "đây là
    mục nói về cái gì" — đúng lỗi làm cả ba bản RecursiveChunker của nhóm trượt
    câu Q3: chúng cắt ngay sau câu chủ đề nên chunk chứa danh sách không còn
    câu nói nó là danh sách của cái gì.

    Corpus Shopee do crawler bê từ web nên hầu như không có `#` của Markdown;
    tiêu đề thật nằm ở dạng dòng viết hoa hoặc mục đánh số ngắn.
    """

    MAX_HEADING_LENGTH = 90

    _MARKDOWN = re.compile(r"^#{1,6}\s+\S")
    # "A. ...", "1. ...", "2.1 ...", "IV. ..." — đứng đầu dòng, theo sau là chữ.
    _NUMBERED = re.compile(r"^(?:[A-ZĐ]|[IVX]{1,4}|\d+(?:\.\d+)*)[.)]\s+\S")

    def __init__(self, chunk_size: int = 800, min_chunk_size: int = 80) -> None:
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size

    def is_heading(self, line: str) -> bool:
        text = line.strip()
        if not text or len(text) > self.MAX_HEADING_LENGTH:
            return False
        if self._MARKDOWN.match(text):
            return True
        # Dòng viết hoa toàn bộ: "CHÍNH SÁCH VẬN CHUYỂN SHOPEE"
        letters = [c for c in text if c.isalpha()]
        if len(letters) >= 8 and text == text.upper():
            return True
        return bool(self._NUMBERED.match(text))

    def _sections(self, text: str) -> list[tuple[str, str]]:
        """Cắt text thành các cặp (tiêu đề, nội dung). Phần trước tiêu đề đầu
        tiên đi kèm tiêu đề rỗng."""
        sections: list[tuple[str, list[str]]] = [("", [])]
        for line in text.splitlines():
            if self.is_heading(line):
                sections.append((line.strip(), []))
            else:
                sections[-1][1].append(line)
        return [(head, "\n".join(body).strip()) for head, body in sections]

    def chunk(self, text: str) -> list[str]:
        if not text.strip():
            return []

        chunks: list[str] = []
        for heading, body in self._sections(text):
            section = f"{heading}\n\n{body}".strip() if heading else body
            if not section:
                continue
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue
            # Mục quá dài: cắt phần thân rồi GẮN LẠI tiêu đề vào từng mảnh.
            budget = self.chunk_size - len(heading) - 2 if heading else self.chunk_size
            pieces = RecursiveChunker(chunk_size=max(budget, 100)).chunk(body)
            chunks.extend(f"{heading}\n\n{piece}".strip() if heading else piece
                          for piece in pieces)

        # Tiêu đề đứng một mình (mục rỗng) thì nhập vào chunk kế tiếp.
        merged: list[str] = []
        for chunk in chunks:
            if merged and len(merged[-1]) < self.min_chunk_size:
                merged[-1] = f"{merged[-1]}\n\n{chunk}"
            else:
                merged.append(chunk)
        return merged


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
