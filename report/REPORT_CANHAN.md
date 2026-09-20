# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Lê Anh Duy
**Nhóm:** ColdBrew
**Ngày:** 20/9/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Hai vector embedding chỉ về gần cùng một hướng trong không gian ngữ nghĩa, tức hai đoạn text nói về cùng một ý — dù dùng từ khác nhau. Giá trị gần 1 = rất giống nghĩa, gần 0 = không liên quan, âm = ngược nghĩa.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Tôi muốn trả lại hàng vì sản phẩm bị lỗi."
- Câu B: "Làm sao để hoàn trả đơn hàng khi nhận được hàng hư hỏng?"
- Tại sao tương đồng: Cùng một ý định (trả hàng do hàng lỗi), chỉ khác cách diễn đạt. Embedding bắt được ngữ nghĩa nên "trả lại hàng" và "hoàn trả đơn hàng" nằm gần nhau, dù gần như không trùng từ nào.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Phí vận chuyển Shopee được tính như thế nào?"
- Câu B: "Hôm nay Hà Nội trời mưa to."
- Tại sao khác: Hai chủ đề không liên quan (chính sách TMĐT vs. thời tiết), không chia sẻ khái niệm nào nên hai vector gần như vuông góc, cosine ≈ 0.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine chỉ quan tâm **hướng**, bỏ qua độ dài vector — nên một đoạn chunk dài và một câu hỏi ngắn cùng chủ đề vẫn được coi là giống nhau, trong khi Euclid sẽ phạt chúng chỉ vì chênh lệch độ lớn. Embedding text mã hóa ý nghĩa ở hướng chứ không ở magnitude, và với vector đã chuẩn hóa thì cosine tương đương dot product nên tính cũng rẻ hơn.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:*
> Bước nhảy (step) giữa 2 chunk liên tiếp = `chunk_size - overlap` = 500 − 50 = **450** ký tự.
> `số chunk = ceil((10000 − 50) / 450) = ceil(9950 / 450) = ceil(22.11) = 23`
> Kiểm chứng bằng `FixedSizeChunker`: các chunk bắt đầu ở 0, 450, 900, …, 9900; chunk cuối là `text[9900:10000]` chỉ còn 100 ký tự → tổng cộng 23 chunk.
> *Đáp án:* **23 chunks**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Step giảm còn 400 → `ceil((10000 − 100) / 400) = ceil(24.75) = 25` chunk, tức tăng thêm 2 chunk (~9%): overlap càng lớn thì chunk càng nhiều, tốn thêm chi phí embedding và lưu trữ. Đổi lại, overlap cao giúp một câu/điều khoản bị cắt ngang ranh giới vẫn xuất hiện trọn vẹn trong ít nhất một chunk — quan trọng với tài liệu chính sách Shopee, nơi một điều khoản bị chẻ đôi sẽ khiến top-1 trả về nửa câu và agent trả lời thiếu ý.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> *Viết 2-3 câu: dùng biểu thức chính quy (regex) gì để phát hiện câu? Xử lý trường hợp ngoại lệ (edge case) nào?*

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> *Viết 2-3 câu: thuật toán hoạt động thế nào? Base case (trường hợp cơ sở) là gì?*

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> *Viết 2-3 câu: lưu trữ thế nào? Tính độ tương tự ra sao?*

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> *Viết 2-3 câu: lọc (filter) trước hay sau? Xóa bằng cách nào?*

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> *Viết 2-3 câu: cấu trúc prompt? Cách đưa ngữ cảnh (inject context) vào thế nào?*

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
# Dán kết quả (output) của: pytest tests/ -v
```

**Số lượng bài test vượt qua (pass):** __ / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | | | cao / thấp | | |
| 2 | | | cao / thấp | | |
| 3 | | | cao / thấp | | |
| 4 | | | cao / thấp | | |
| 5 | | | cao / thấp | | |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> *Viết 2-3 câu:*

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** __ / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> *Viết 2-3 câu:*

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | / 5 |
| Hướng tiếp cận của tôi (My Approach) | / 10 |
| Hoàn thiện code (Core Implementation — tests) | / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | / 5 |
| Kết quả truy xuất của tôi (Competition Results) | / 10 |
| **Tổng phần cá nhân** | **/ 60** |
