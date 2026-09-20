"""Các ca ngoại lệ của chunker trên văn bản quy định tiếng Việt.

Bộ test của lab chỉ kiểm cấu trúc (kiểu trả về, số lượng chunk). File này giữ
lại những ca đã thực sự hỏng khi chạy trên corpus Shopee, để chúng không âm
thầm hỏng lại: viết tắt, số thập phân, URL, ellipsis giữa câu, đánh số mục,
và chunk vụn 1 ký tự do đầu mục bị xả riêng.

    pytest tests_extra/ -v
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


# --- HeadingChunker: chunker tuỳ chỉnh cho văn bản quy định ---

HEADING_DOC = (
    "3. ĐIỀU KIỆN YÊU CẦU TRẢ HÀNG/HOÀN TIỀN\n\n"
    + "Người Mua chỉ có thể yêu cầu trả hàng trong các trường hợp sau. " * 40
    + "\n\n4. QUY ĐỊNH BỔ SUNG\n\nMục này rất ngắn.\n"
)


def test_heading_chunker_nhan_dien_tieu_de():
    from src.chunking import HeadingChunker

    chunker = HeadingChunker()
    assert chunker.is_heading("A. PHẠM VI VÀ ĐỐI TƯỢNG ÁP DỤNG")
    assert chunker.is_heading("1. Đối tượng áp dụng")
    assert chunker.is_heading("## Mục lục")
    # Điều khoản dài KHÔNG phải tiêu đề, dù cũng mở đầu bằng số
    assert not chunker.is_heading(
        "3.1. Người Mua đồng ý rằng Người Mua chỉ có thể yêu cầu trả hàng/hoàn tiền "
        "trong các trường hợp được liệt kê dưới đây và phải tuân thủ mọi điều kiện."
    )
    assert not chunker.is_heading("")


def test_heading_chunker_gan_lai_tieu_de_vao_moi_manh():
    """Mục dài bị cắt nhỏ thì MỌI mảnh con phải còn tiêu đề của nó.

    Thiếu bước này là lỗi làm cả ba bản RecursiveChunker của nhóm trượt Q3.
    """
    from src.chunking import HeadingChunker

    chunks = HeadingChunker(chunk_size=400).chunk(HEADING_DOC)
    covering = [c for c in chunks if "trả hàng trong các trường hợp" in c]
    assert len(covering) > 1, "mục dài lẽ ra phải bị cắt thành nhiều mảnh"
    assert all(c.startswith("3. ĐIỀU KIỆN YÊU CẦU") for c in covering)


def test_heading_chunker_moi_chunk_deu_co_tieu_de():
    """Bất biến thật của chunker này: không chunk nào đứng trơ không có tiêu đề.

    Một mục ngắn vẫn hợp lệ nếu nó trọn vẹn — cái phải tránh là mảnh mất ngữ
    cảnh, chứ không phải chunk ngắn.
    """
    from src.chunking import HeadingChunker

    chunker = HeadingChunker(chunk_size=400)
    chunks = chunker.chunk(HEADING_DOC)
    assert chunks
    for chunk in chunks:
        assert chunker.is_heading(chunk.splitlines()[0]), f"chunk không có tiêu đề: {chunk[:60]!r}"


@pytest.mark.skipif(not CORPUS, reason="chưa thu thập corpus")
def test_heading_chunker_tren_corpus_that():
    from src.chunking import HeadingChunker
    from src.indexing import chunk_corpus

    documents = chunk_corpus(HeadingChunker(chunk_size=800))
    assert len(documents) > 100
    # Offset phải trỏ vào đúng tài liệu, không được vượt quá độ dài phần thân.
    for doc in documents:
        assert doc.metadata["start"] < doc.metadata["end"]
