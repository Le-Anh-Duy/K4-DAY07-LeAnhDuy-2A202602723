"""Sinh data/shopee-ecommerce/gold.json — bộ 5 benchmark query của nhóm ColdBrew.

Vùng gold được khai bằng offset ký tự trên PHẦN THÂN tài liệu (sau YAML
frontmatter), nửa khoảng [start, end). Chạy lại script này sau mỗi lần thu thập
lại corpus: các assert bên dưới sẽ báo ngay nếu offset trôi.

    python scripts/make_gold.py
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "shopee-ecommerce"


def body(doc_id: str) -> str:
    """Phần thân tài liệu, bỏ YAML frontmatter — đây là chuỗi mà offset bám vào."""
    return (DATA_DIR / f"{doc_id}.md").read_text(encoding="utf-8").split("---", 2)[2].lstrip("\n")


QUERIES = [
    dict(id="Q1", question_type="tra_so_lieu",
         query="Mua hàng trên Shopee Mall, sau khi yêu cầu trả hàng được chấp thuận thì phải gửi trả sản phẩm trong bao nhiêu ngày?",
         gold_answer="06 ngày lịch kể từ ngày yêu cầu trả hàng/hoàn tiền được chấp thuận; phải đóng gói trong hoặc kèm bao bì ban đầu và dán kèm Phiếu Trả Hàng do Shopee cung cấp.",
         gold_spans=[("77262", 2628, 3865)],
         anchor="06 (sáu) ngày lịch", metadata_filter=None),
    dict(id="Q2", question_type="tra_so_lieu",
         query="Hàng bị hư hại trong quá trình vận chuyển thì phải khiếu nại trong vòng bao nhiêu ngày?",
         gold_answer="Hỏi với tư cách Người Mua: gửi yêu cầu trả hàng/hoàn tiền trong vòng 15 ngày kể từ khi đơn hàng được cập nhật giao hàng thành công, riêng thực phẩm tươi sống và đông lạnh là 24 giờ. (Cùng câu hỏi này, Người Bán lại có mốc khác: 03 ngày khi hàng hư hại và 07 ngày khi hàng thất lạc lúc hoàn trả, theo 77250 mục D.1.b.)",
         gold_spans=[("77251", 3085, 3595)],
         anchor="trong vòng 24 giờ kể từ lúc đơn hàng được cập nhật giao hàng thành công",
         metadata_filter={"audience": "buyer"},
         note="Cau duy nhat can metadata_filter. Cau hoi co y khong neu nguoi hoi la ai nen co HAI dap an dung tuy doi tuong. Khong loc thi bang xep hang nghieng han ve 77250 (seller) vi cau hoi mang tu vung 'van chuyen'/'khieu nai' cua tai lieu do, nen nguoi mua nhan ve dap an danh cho nguoi ban. Loc audience=buyer moi ra dung moc 15 ngay/24 gio."),
    dict(id="Q3", question_type="hoi_dieu_kien",
         query="Người mua được yêu cầu trả hàng/hoàn tiền trong những trường hợp nào?",
         gold_answer="Không nhận được hàng / không nhận đủ hàng / nhận phải hàng giả, hàng nhái; sản phẩm bị lỗi hoặc hư hại khi vận chuyển; người bán giao sai sản phẩm (sai kích cỡ, sai màu sắc); hàng khác biệt rõ rệt so với mô tả; sản phẩm hết hạn sử dụng; người bán tự thỏa thuận đồng ý cho trả hàng; hàng còn nguyên vẹn nguyên bao bì nhưng người mua không còn nhu cầu (Trả hàng COM).",
         gold_spans=[("77251", 2180, 3085)],
         anchor="sai kích cỡ, sai màu sắc", metadata_filter=None),
    dict(id="Q4", question_type="hoi_quy_trinh",
         query="Quy trình giải quyết tranh chấp của Shopee gồm mấy bước và Shopee đưa ra hướng giải quyết trong bao lâu?",
         gold_answer="4 bước. Với tranh chấp không phải khiếu nại Trả hàng/Hoàn tiền, Shopee đưa ra hướng giải quyết trong vòng 07 ngày làm việc kể từ ngày nhận đủ thông tin/tài liệu liên quan; vụ việc phức tạp thì thời hạn kéo dài hơn.",
         gold_spans=[("77265", 907, 2658), ("77245", 14121, 15870)],
         anchor="trong vòng 07 ngày làm việc kể từ ngày nhận được đầy đủ", metadata_filter=None,
         note="Quy Che Hoat Dong 77245 chep lai nguyen khoi quy trinh nay cua 77265 nen ca hai deu la vung gold hop le."),
    dict(id="Q5", question_type="liet_ke",
         query="Những nội dung nào bị nghiêm cấm đăng bán trên Shopee?",
         gold_answer="Nội dung phản động, chống phá, bài xích tôn giáo, khiêu dâm, bạo lực, xâm phạm chủ quyền/an ninh quốc gia; thông tin rác làm mất uy tín dịch vụ Shopee; xúc phạm người khác; tuyên truyền điều pháp luật nghiêm cấm; quảng cáo sản phẩm độc hại; văn hóa phẩm đồi trụy; tài liệu bí mật quốc gia, bí mật nhà nước, bí mật kinh doanh, bí mật cá nhân; và các sản phẩm thuộc Danh sách cấm/hạn chế của Shopee.",
         gold_spans=[("77246", 1279, 2847), ("77245", 52118, 52876)],
         anchor="bí mật quốc gia", metadata_filter=None,
         note="Quy Che Hoat Dong 77245 chep lai danh muc noi dung cam nay cua 77246."),
]


def build() -> dict:
    all_docs = sorted(p.stem for p in DATA_DIR.glob("*.md"))
    for item in QUERIES:
        spans = {doc: (lo, hi) for doc, lo, hi in item["gold_spans"]}
        # Anchor chi duoc phep xuat hien BEN TRONG vung gold, tren toan corpus.
        # Neu no lot ra cho khac thi phep kiem muc noi dung se pass gia, dung cai
        # bay "thoi phong ket qua" ma CP6 canh bao.
        for doc_id in all_docs:
            text = body(doc_id)
            hits = [i for i in range(len(text)) if text.startswith(item["anchor"], i)]
            if doc_id not in spans:
                assert not hits, f'{item["id"]}: anchor lọt sang {doc_id}'
                continue
            lo, hi = spans[doc_id]
            assert hits, f'{item["id"]}: anchor vắng trong {doc_id}'
            assert all(lo <= i < hi for i in hits), f'{item["id"]}: anchor ngoài vùng gold {doc_id} tại {hits}'

        item["gold_chunk_ids"] = [f"{doc}_{lo}_{hi}" for doc, lo, hi in item["gold_spans"]]
        doc, lo, hi = item["gold_spans"][0]
        item["evidence"] = body(doc)[lo:hi].strip()
        item["gold_spans"] = [dict(doc_id=d, start=s, end=e) for d, s, e in item["gold_spans"]]

    return {
        "corpus": "data/shopee-ecommerce",
        "chunk_id_scheme": "{doc_id}_{start_offset}_{end_offset} — offset ký tự trên phần thân tài liệu (sau YAML frontmatter), nửa khoảng [start, end)",
        "hit_rule": "chunk [s,e) của tài liệu X trúng vùng gold khi tồn tại span của X với s < end and e > start; đồng thời ngữ cảnh top-k phải chứa chuỗi anchor",
        "scoring": "2 điểm nếu gold ở top-1 và ngữ cảnh chứa anchor; 1 điểm nếu gold ở top-2/3; 0 nếu vắng khỏi top-3",
        "queries": QUERIES,
    }


if __name__ == "__main__":
    data = build()
    out_path = DATA_DIR / "gold.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in data["queries"]:
        print(f'{item["id"]}  {",".join(item["gold_chunk_ids"]):40} anchor={item["anchor"]!r}')
    print(f"OK — {len(data['queries'])} query, ghi vào {out_path}")
