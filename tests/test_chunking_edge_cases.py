"""Các ca ngoại lệ của chunker trên văn bản quy định tiếng Việt.

Bộ test của lab chỉ kiểm cấu trúc (kiểu trả về, số lượng chunk). File này giữ
lại những ca đã thực sự hỏng khi chạy trên corpus Shopee, để chúng không âm
thầm hỏng lại: viết tắt, số thập phân, URL, ellipsis giữa câu, đánh số mục,
và chunk vụn 1 ký tự do đầu mục bị xả riêng.

    pytest tests/test_chunking_edge_cases.py -v
"""

from pathlib import Path

import pytest

from src.chunking import RecursiveChunker, SentenceChunker

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "shopee-ecommerce"


def body(path: Path) -> str:
    return path.read_text(encoding="utf-8").split("---", 2)[2].lstrip("\n")


CORPUS = sorted(DATA_DIR.glob("*.md"))


# (văn bản, số câu mong đợi khi max_sentences_per_chunk=1)
SENTENCE_CASES = [
    ("TS. Nguyễn Văn A giảng bài. Sinh viên nghe.", 2),          # viết tắt học hàm
    ("Giá là 1.5 triệu đồng. Rất rẻ.", 2),                        # số thập phân
    ("Xem thêm tại help.shopee.vn nhé. Cảm ơn.", 2),              # tên miền
    ("Liên hệ test@domain.vn để biết thêm. Xin cảm ơn.", 2),      # email
    ("Anh ấy nói... rồi im lặng. Tôi hiểu.", 2),                  # ellipsis giữa câu
    ("Sản phẩm gồm áo, quần, v.v. Người bán phải đóng gói.", 1),  # v.v.
    ('Anh ta hỏi "Bao giờ giao?" rồi đi. Tôi trả lời.', 2),       # dấu đóng ngoặc kép
    ("3.1. Người Mua đồng ý điều này. 3.2. Thời hạn là 15 ngày.", 2),  # đánh số điều khoản
    ("a. Hàng cấm bán. b. Hàng giả.", 2),                         # đầu mục chữ cái
    ("XII. QUY ĐỊNH CHUNG Phần này áp dụng cho mọi bên.", 1),     # số La Mã đầu mục
    ("Phiên bản v2.0 đã phát hành. Tải ngay.", 2),                # số phiên bản
]


@pytest.mark.parametrize("text,expected", SENTENCE_CASES)
def test_sentence_boundaries(text, expected):
    assert len(SentenceChunker(max_sentences_per_chunk=1).chunk(text)) == expected


def test_sentence_chunker_caps_runaway_blocks():
    """Liệt kê ngăn bằng dấu chấm phẩy không có dấu kết câu -> phải bị cắt theo max_chars."""
    runaway = "; ".join(f"({chr(97 + i)}) điều khoản dài dòng số {i} " * 6 for i in range(12))
    chunks = SentenceChunker(max_sentences_per_chunk=3, max_chars=1000).chunk(runaway)
    assert chunks and max(len(c) for c in chunks) <= 1000


def test_recursive_chunker_keeps_list_marker_with_its_item():
    """Đầu mục 'm.' không được tách thành chunk riêng 1 ký tự."""
    text = "m. " + "Các sản phẩm nằm trong Danh sách cấm của Shopee. " * 30
    chunks = RecursiveChunker(chunk_size=200).chunk(text)
    assert min(len(c) for c in chunks) > 1
    assert chunks[0].startswith("m.")


@pytest.mark.skipif(not CORPUS, reason="chưa thu thập corpus")
@pytest.mark.parametrize("path", CORPUS, ids=lambda p: p.stem)
def test_no_degenerate_chunks_on_real_corpus(path):
    text = body(path)
    for chunker, limit in [(SentenceChunker(3, max_chars=1000), 1000), (RecursiveChunker(chunk_size=800), 800)]:
        chunks = chunker.chunk(text)
        assert chunks
        assert max(len(c) for c in chunks) <= limit
        assert min(len(c) for c in chunks) > 1
