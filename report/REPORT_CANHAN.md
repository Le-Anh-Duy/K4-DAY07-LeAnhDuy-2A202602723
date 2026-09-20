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

Tôi **không dùng `re.split`** mà quét ứng viên ngắt câu bằng `finditer` rồi phủ quyết từng chỗ bằng Python thường. Lý do: bản đầu tôi viết lookbehind kiểu `(?<!(?:TS|ThS|v\.v))` để chặn viết tắt, nhưng `re` của Python **bắt buộc lookbehind có độ rộng cố định**, mà các nhánh này dài ngắn khác nhau nên `re.compile` ném `re.error: look-behind requires fixed-width pattern` ngay trong `__init__` — cả 7 test liên quan fail. Quét rồi phủ quyết bỏ được ràng buộc đó và đọc cũng dễ hơn.

Regex tìm ứng viên là `[.!?…]+[\"'’”»)\]]*(?=\s|$)`: bắt cụm dấu kết câu kèm dấu đóng ngoặc/ngoặc kép đi liền, và **bắt buộc phía sau là khoảng trắng**. Riêng ràng buộc cuối này đã xử lý xong một loạt ca ngoại lệ mà không cần luật riêng — `1.5`, `v2.0`, `help.shopee.vn`, `test@domain.vn` đều có dấu chấm nằm giữa hai ký tự không phải khoảng trắng nên không bao giờ thành ứng viên.

Bốn phủ quyết còn lại, nhìn vào **token đứng ngay trước** dấu chấm:

| Phủ quyết | Ví dụ bị chặn | Vì sao cần |
|---|---|---|
| Từ viết tắt trong `ABBREVIATIONS` | `TS.`, `ThS.`, `Mr.`, `v.v.` | Danh xưng và "vân vân" rất hay đứng giữa câu |
| Đánh số điều khoản `^\d+(\.\d+)*$` | `3.1.`, `10.2.3.` | Corpus Shopee đánh số dày đặc; ngắt ở đây sẽ tách `"3.1."` thành mảnh 4 ký tự và điều khoản mất luôn số hiệu |
| Một chữ cái đơn | `a.`, `b.`, `A. Nguyễn` | Vừa là đầu mục liệt kê vừa là viết tắt tên riêng |
| Số La Mã **viết hoa** | `XII.` | Bắt buộc `isupper()` để không nhận nhầm từ tiếng Việt như "vi", "mi" |

Thêm một phủ quyết nhìn về **phía sau**: nếu ký tự đầu tiên sau dấu chấm là **chữ thường** thì đó là dấu chấm giữa câu, không phải kết câu — đây là cách duy nhất bắt được `"Anh ấy nói... rồi im lặng."` và `'Anh ta hỏi "Bao giờ giao?" rồi đi.'`. Ngoại lệ của ngoại lệ: đầu mục liệt kê (`a.`, `iv.`) cũng viết thường nhưng đúng là mục mới, nên có `_LIST_MARKER` chừa ra.

**Edge case tôi biết là vẫn chưa xử lý được:** viết tắt nằm ngoài danh sách `ABBREVIATIONS` vẫn bị cắt sai — đây là cách tiếp cận theo từ điển nên không thể phủ hết. Muốn triệt để thì phải dùng mô hình tách câu đã huấn luyện (`underthesea`, `pyvi`), nhưng như vậy là thêm một phụ thuộc chỉ để xử lý vài trường hợp hiếm trong corpus này.

**Một phát hiện từ dữ liệu thật, không phải từ regex:** đo trên corpus thì có chunk dài **3025 ký tự**. Không phải lỗi tách câu — văn bản quy định liệt kê bằng **dấu chấm phẩy** (`(m) ...; (n) ...;`) và bảng phí thì **không có dấu kết câu nào**, nên cả khối là một "câu" hợp lệ. Đếm câu không cứu được ca này, nên tôi thêm trần `max_chars=1000`; khối nào vượt thì hạ xuống `RecursiveChunker` thay vì viết logic cắt mới. Sau khi thêm: chunk dài nhất toàn corpus còn **998** ký tự.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:

Thuật toán chạy **hai chiều** trên cùng một vòng lặp, và tôi nghĩ phần lớn người viết chỉ làm một chiều:

- *Đệ quy xuống:* cắt bằng separator ưu tiên cao nhất (`"\n\n"` — ranh giới đoạn) để giữ ngữ nghĩa lớn; mảnh nào vẫn dài hơn `chunk_size` thì gọi lại `_split` với danh sách separator còn lại (`"\n"` → `". "` → `" "` → `""`).
- *Gom lên:* các mảnh nhỏ liền kề được nối vào `buffer` cho tới sát `chunk_size`. Thiếu bước này, một file toàn dòng ngắn sẽ sinh ra hàng trăm chunk vụn 5–10 ký tự.

**Ba base case:** text rỗng sau `strip()` → `[]`; text đã vừa `chunk_size` → `[text]`; hết separator (kể cả khi người dùng truyền thẳng `separators=[]`, đúng ca của test `test_empty_separators_falls_back_gracefully`) → cắt cứng theo `chunk_size` bằng `_hard_cut`.

**Bug tôi tìm ra khi chạy trên corpus thật:** chunker đẻ ra chunk dài **đúng 1 ký tự** — `'m'` và `'l'`. Truy ra nguyên nhân: dòng `m. Các sản phẩm nằm trong Danh sách cấm…` bị tách ở separator `". "` thành `["m", "Các sản phẩm…"]`; phần đuôi dài hơn `chunk_size` nên code cũ **xả `buffer` ra thành chunk riêng** rồi mới đệ quy trên `piece`. Kết quả là đầu mục `"m"` thành một chunk vô nghĩa, còn nội dung mục đó thì mất luôn nhãn của mình.

Cách sửa: khi gặp `piece` quá dài thì đệ quy trên **cả `candidate`** (tức `buffer + separator + piece`) thay vì chỉ `piece`, nhờ đó đầu mục dính liền với nội dung của nó và dấu phân cách cũng được giữ. Sau khi sửa: **không còn chunk nào dưới 2 ký tự** trên cả 7 tài liệu, và mọi chunk đều ≤ `chunk_size`.

Tôi để lại `tests/test_chunking_edge_cases.py` — 11 ca ngoại lệ ở trên, cộng hai bất biến chạy trên corpus thật (không chunk nào vượt trần, không chunk nào ≤ 1 ký tự) để các lỗi này không âm thầm quay lại.

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
