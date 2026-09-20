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
> Hai vector chỉ về gần cùng một hướng trong không gian ngữ nghĩa, tức hai đoạn text nói cùng một ý dù dùng từ khác nhau. Gần 1 = rất giống nghĩa, gần 0 = không liên quan, âm = ngược nghĩa.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Tôi muốn trả lại hàng vì sản phẩm bị lỗi."
- Câu B: "Làm sao để hoàn trả đơn hàng khi nhận được hàng hư hỏng?"
- Tại sao tương đồng: Cùng ý định (trả hàng do hàng lỗi), chỉ khác cách diễn đạt — gần như không trùng từ nào nhưng embedding vẫn đặt chúng cạnh nhau.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Phí vận chuyển Shopee được tính như thế nào?"
- Câu B: "Hôm nay Hà Nội trời mưa to."
- Tại sao khác: Hai chủ đề không liên quan (chính sách TMĐT vs. thời tiết), không chia sẻ khái niệm nào nên hai vector gần như vuông góc.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine chỉ xét hướng, bỏ qua độ dài vector — chunk dài và câu hỏi ngắn cùng chủ đề vẫn giống nhau, trong khi Euclid phạt chúng chỉ vì chênh lệch độ lớn. Vector đã chuẩn hóa thì cosine bằng đúng dot product nên tính cũng rẻ hơn.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Step = 500 − 50 = 450 → `ceil((10000 − 50) / 450) = ceil(22.11)` = **23 chunks**. Kiểm lại bằng `FixedSizeChunker`: chunk bắt đầu ở 0, 450, …, 9900, chunk cuối chỉ còn 100 ký tự — đúng 23.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Step còn 400 → `ceil(9900 / 400)` = **25 chunks**, tăng 2 chunk nên tốn thêm chi phí embedding. Đổi lại, overlap lớn giúp điều khoản bị cắt ngang ranh giới vẫn nguyên vẹn trong ít nhất một chunk — tránh top-1 trả về nửa câu.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Quét ứng viên bằng `[.!?…]+[\"'’”»)\]]*(?=\s|$)` rồi phủ quyết bằng Python thay vì `re.split` (lookbehind biến độ rộng không compile được). Ràng buộc "phải có khoảng trắng phía sau" tự loại `1.5`, `v2.0`, URL, email; phủ quyết thêm cho viết tắt `TS.`/`v.v.`, đánh số `3.1.`, La Mã `XII.` và ký tự kế tiếp viết thường. Thêm trần `max_chars=1000` vì corpus có "câu" dài 3025 ký tự do liệt kê bằng dấu chấm phẩy.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Cắt theo separator ưu tiên cao trước (`"\n\n"` → `"\n"` → `". "` → `" "` → `""`), mảnh nào còn dài hơn `chunk_size` thì đệ quy xuống separator kế tiếp, đồng thời gom các mảnh nhỏ liền kề vào `buffer` cho tới sát `chunk_size`. Ba base case: rỗng → `[]`, vừa cỡ → `[text]`, hết separator (kể cả `separators=[]`) → cắt cứng. Khi đệ quy phải truyền cả `buffer + separator + piece` chứ không riêng `piece`, nếu không đầu mục `m.` bị xả riêng thành chunk 1 ký tự.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Bỏ hẳn nhánh ChromaDB, chỉ dùng list record trong bộ nhớ: mỗi `Document` thành một record gồm `id`, `content`, bản **copy** của metadata và embedding tính sẵn lúc nạp. `search` embed query rồi chấm điểm bằng `compute_similarity` (cosine thật, không dùng dot product trần — để còn đúng khi đổi sang backend không chuẩn hóa vector), sắp giảm dần rồi cắt `top_k` và bỏ trường `embedding` khỏi kết quả.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> **Lọc trước rồi mới xếp hạng.** Lấy `top_k` trước rồi mới loại cái không khớp thì có thể còn 0 kết quả dù store vẫn còn tài liệu hợp lệ, vì k chỗ đã bị tài liệu sai chiếm hết. Cả `search` và `search_with_filter` đều gọi chung helper `_rank`, chỉ khác tập ứng viên nên kết quả không thể lệch nhau. `delete_document` lọc bỏ mọi record có `metadata['doc_id']` khớp rồi so số lượng trước/sau để trả `True`/`False` — `add_documents` đã `setdefault("doc_id", doc.id)` nên tài liệu nạp với metadata rỗng vẫn xoá được.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Ba nhịp: truy xuất top-k → dựng prompt → gọi `llm_fn`. Ngữ cảnh được đánh số `[1] [2] [3]` kèm nguồn (`source_url` → `source` → `doc_id`) và prompt yêu cầu model trích dẫn số hiệu đó, nhờ vậy câu trả lời truy vết được về đúng chunk và đúng file (tiêu chí *Source Traceability*). Prompt ràng buộc chỉ dùng ngữ cảnh được cấp; store rỗng hoặc filter loại hết thì trả thẳng câu thông báo chứ không gọi LLM vô ích.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0 -- D:\Coding\Vin AI Thực Chiến\Lab Work\K4-DAY07-LeAnhDuy-2A202602723\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Coding\Vin AI Thực Chiến\Lab Work\K4-DAY07-LeAnhDuy-2A202602723
tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
... (36 test còn lại đều PASSED) ...
============================= 42 passed in 0.04s ==============================
```

**Số lượng bài test vượt qua (pass):** **42** / 42

> Ngoài ra `pytest tests_extra/ -q` → 20 passed: bộ test edge case tự viết cho chunker (viết tắt, số thập phân, URL, đánh số điều khoản, số La Mã, ellipsis giữa câu) cùng hai bất biến chạy trên corpus thật.

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

> Đo bằng `gemini-embedding-001` (768 chiều, `task_type=SEMANTIC_SIMILARITY`), ngưỡng phân loại đặt ở 0.6.

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Tôi muốn trả lại hàng vì sản phẩm bị lỗi. | Làm sao để hoàn trả đơn hàng khi nhận được hàng hư hỏng? | cao | **0.912** | ✓ |
| 2 | Phí vận chuyển Shopee được tính như thế nào? | Hôm nay Hà Nội trời mưa to. | thấp | **0.655** | ✗ |
| 3 | Người bán phải đóng gói hàng hóa đúng quy định trước khi giao. | Người mua được quyền trả hàng trong vòng 15 ngày. | thấp | **0.784** | ✗ |
| 4 | Đơn hàng bị hủy do người bán hết hàng. | Người bán không xác nhận đơn nên đơn hàng bị hủy. | cao | **0.938** | ✓ |
| 5 | Shopee cấm bán hàng giả. | Shopee nghiêm cấm đăng bán sản phẩm nhái thương hiệu. | cao | **0.959** | ✓ |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 2: hai câu **không liên quan gì nhau** (phí vận chuyển vs thời tiết) vẫn đạt 0.655 — model có một "sàn tương tự" khá cao, chỉ cần cùng là tiếng Việt đã gần nhau sẵn, nên **giá trị cosine tuyệt đối gần như vô nghĩa**, chỉ thứ hạng tương đối mới dùng được. Cặp 3 cho thấy embedding mã hóa **chủ đề** chứ không mã hóa **vai trò**: hai câu cùng nói về chính sách Shopee nhưng khác hẳn đối tượng và nội dung vẫn được 0.784 — đây đúng là lý do câu hỏi không nêu người hỏi cần `metadata_filter` mới tách được người mua với người bán.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

> Chiến lược của tôi: `RecursiveChunker(chunk_size=800)` → 419 chunk. Backend `gemini-embedding-001` (768 chiều). Output đầy đủ: `ket_qua_benchmark.txt`. `llm_fn` ở bước benchmark là hàm giả nên cột cuối mô tả ngữ cảnh truy xuất được có đủ để trả lời hay không.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Shopee Mall: gửi trả sản phẩm trong bao nhiêu ngày? | `77262_2637_3355` — mục 1.2, "Sau khi Người Mua yêu cầu trả hàng/hoàn tiền…" | 0.826 | **Có** (2/2) | Ngữ cảnh chứa đúng mốc "06 (sáu) ngày lịch" |
| 2 | Hàng hư hại khi vận chuyển, khiếu nại trong bao nhiêu ngày? *(lọc `audience=buyer`)* | `77251_2282_2946` — các trường hợp được trả hàng/hoàn tiền | 0.729 | **Không** (0/2) | Lọc đúng tài liệu người mua nhưng trúng mục 3.1 thay vì 3.2, thiếu mốc 15 ngày |
| 3 | Người mua được trả hàng/hoàn tiền trong trường hợp nào? | `77243_55042_55775` — điều kiện hủy đơn ở giai đoạn "Chờ Xác Nhận" | 0.787 | **Không** (0/2) | Đúng chủ đề hoàn tiền nhưng sai tài liệu, không liệt kê được 7 trường hợp |
| 4 | Quy trình giải quyết tranh chấp gồm mấy bước, xử lý bao lâu? | `77245_14704_15247` — "Bước 3: Khiếu nại Trả Hàng/Hoàn Tiền…" | 0.815 | **Có** (2/2) | Ngữ cảnh chứa "07 ngày làm việc" và đủ 4 bước |
| 5 | Nội dung nào bị nghiêm cấm đăng bán? | `77245_52118_52876` — "a. Phản động, chống phá, bài xích tôn giáo…" | 0.817 | **Có** (2/2) | Ngữ cảnh chứa trọn danh mục a–m |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **3** / 5 — tổng **6/10 điểm** (Q1, Q4, Q5 đạt 2/2; Q2 và Q3 đều 0/2).

> Tôi chạy thêm hai chiến lược còn lại trên cùng code của mình: **`fixed` 8/10** và **`sentence` 7/10**, tức chiến lược tôi chọn (`recursive`) lại là chiến lược **kém nhất** trong ba. Nguyên nhân ở mục phân tích lỗi bên dưới. Bảng đối chiếu 11 ô của cả nhóm nằm ở `REPORT_NHOM.md` mục 2 và `ket_qua_benchmark.txt`.

> **Phân tích lỗi — Q2 và Q3 hỏng cùng một kiểu.** Cả hai đều bị chunk *đúng chủ đề nhưng không chứa con số trả lời được* đánh bại chunk có đáp án: cosine đo độ giống chủ đề chứ không đo mật độ thông tin. Q2 còn cho thấy filter chỉ giải quyết được một nửa — lọc `audience=buyer` đã kéo đúng tài liệu 77251 lên top-3, nhưng trong cùng tài liệu thì mục 3.1 (điều kiện trả hàng) vẫn thắng mục 3.2 (thời hạn 15 ngày) vì câu hỏi dùng từ "khiếu nại" hợp với mục 3.1 hơn.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> *(điền sau buổi demo)*

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá | Căn cứ |
|----------|-------------------|--------|
| Khởi động (Warm-up) | **5** / 5 | Đủ 2 bài: cosine (kèm cặp cao/thấp trong domain) và phép tính chunking 23 chunk, có kiểm chứng ngược bằng `FixedSizeChunker` |
| Hướng tiếp cận của tôi (My Approach) | **9** / 10 | Giải thích đủ 5 phần của `src`, kèm lý do thiết kế và 2 lỗi tự tìm ra khi chạy trên dữ liệu thật. Trừ 1 vì phần `agent.answer` còn mỏng |
| Hoàn thiện code (Core Implementation — tests) | **30** / 30 | `pytest tests/ -v` → 42/42 passed, không còn `NotImplementedError`; `main.py` chạy trọn vẹn |
| Dự đoán độ tương tự (Similarity Predictions) | **5** / 5 | Đủ 5 cặp đo bằng embedding thật, 2/5 dự đoán sai và phần phản ngẫm rút ra được kết luận dùng được (cosine tuyệt đối vô nghĩa) |
| Kết quả truy xuất của tôi (Competition Results) | **6** / 10 | Chiến lược tôi chọn (`recursive`) đạt đúng 6/10. Chạy thêm `fixed` 8/10 và `sentence` 7/10 để đối chiếu, kèm phân tích nguyên nhân 2 câu hỏng |
| **Tổng phần cá nhân** | **55 / 60** | |
