# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** ColdBrew
**Thành viên:** Lê Anh Duy, Đào Trọng Khang, Lê Quang Thành, Nguyễn Thị Phương Duyên
**Ngày:** 20/9/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Shopee ecommerce — bộ chính sách & điều khoản công khai trên Shopee Trung tâm trợ giúp (help.shopee.vn/portal/4)

**Tại sao nhóm chọn chủ đề này?**
> Shopee đông người dùng nhưng hầu như không ai đọc hết các trang chính sách dài hàng chục nghìn ký tự — đúng bài toán RAG giải quyết tốt. Tài liệu công khai, có cấu trúc điều khoản đánh số nên đáp án kiểm chứng được, và corpus chia tự nhiên theo người mua / người bán để thử lọc metadata.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | ĐIỀU KHOẢN DỊCH VỤ | https://help.shopee.vn/portal/4/article/77243 | 2026-09-20 / not-stated | 111.467 | doc_id=77243, audience=both |
| 2 | QUY CHẾ HOẠT ĐỘNG SÀN TMĐT SHOPEE.VN | https://help.shopee.vn/portal/4/article/77245 | 2026-09-20 / not-stated | 103.138 | doc_id=77245, audience=both |
| 3 | QUY ĐỊNH VỀ ĐĂNG BÁN SẢN PHẨM TRÊN SHOPEE | https://help.shopee.vn/portal/4/article/77246 | 2026-09-20 / not-stated | 29.255 | doc_id=77246, audience=seller |
| 4 | CHÍNH SÁCH VẬN CHUYỂN SHOPEE | https://help.shopee.vn/portal/4/article/77250 | 2026-09-20 / not-stated | 33.216 | doc_id=77250, audience=**seller** |
| 5 | CHÍNH SÁCH TRẢ HÀNG VÀ HOÀN TIỀN | https://help.shopee.vn/portal/4/article/77251 | 2026-09-20 / not-stated | 26.385 | doc_id=77251, audience=**buyer** |
| 6 | Điều Khoản Dịch Vụ của Shopee Mall | https://help.shopee.vn/portal/4/article/77262 | 2026-09-20 / not-stated | 44.897 | doc_id=77262, audience=both |
| 7 | QUY TRÌNH GIẢI QUYẾT TRANH CHẤP / XỬ LÝ KHIẾU NẠI | https://help.shopee.vn/portal/4/article/77265 | 2026-09-20 / not-stated | 6.737 | doc_id=77265, audience=both |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

> 7 trang đều lấy từ Trung tâm trợ giúp công khai, không cần đăng nhập (`license_or_permission = public-source`); Shopee không ghi số phiên bản nên `document_version = not-stated`, dùng `retrieved_at` làm mốc. `audience` gán theo tần suất "Người Mua"/"Người Bán" trong từng văn bản: 77250 = `seller` (mục D.1.b ghi rõ "dành cho Người Bán"), 77251 = `buyer`.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `77250` | Khóa duy nhất của tài liệu: gom/lọc chunk theo tài liệu, xóa & nạp lại một tài liệu mà không đụng phần còn lại (`store.delete_document`). |
| `title` | string | `CHÍNH SÁCH VẬN CHUYỂN SHOPEE` | Hiển thị nguồn khi agent trả lời, và giúp người đọc kiểm chứng chunk nào thuộc chính sách nào. |
| `source_url` | string (URL) | `https://help.shopee.vn/portal/4/article/77250` | Trích dẫn nguồn trong câu trả lời — người dùng bấm vào xem điều khoản gốc. |
| `retrieved_at` | date | `2026-09-20` | Chính sách TMĐT thay đổi thường xuyên; cho phép cảnh báo dữ liệu cũ hoặc ưu tiên bản mới khi nạp lại. |
| `document_version` | string | `not-stated` | Phân biệt các phiên bản điều khoản khi Shopee cập nhật; hiện để `not-stated` vì trang không ghi số hiệu. |
| `audience` | enum (`buyer`/`seller`/`both`) | `seller` | Trường dùng để **lọc metadata**: câu "hàng hư hỏng khi vận chuyển thì khiếu nại trong bao nhiêu ngày?" không nêu người hỏi là ai, mà 77250 (seller) và 77251 (buyer) cùng từ vựng nhưng khác thời hạn. Không lọc thì top-3 lẫn hai file và agent trả lời sai đối tượng. Phân bố: 4 `both`, 2 `seller`, 1 `buyer`. |
| `license_or_permission` | string | `public-source` | Bằng chứng quản trị dữ liệu: chứng minh mọi chunk trong store đều đến từ nguồn được phép dùng. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

> Chạy `compare(body, chunk_size=800)` trên phần thân tài liệu (đã bỏ frontmatter, nếu không là đang đo cả khối YAML).

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| 77251 Trả hàng & hoàn tiền | FixedSizeChunker (`fixed_size`) | 28 | 778 | Kém — cắt cứng giữa câu, điều khoản bị chẻ đôi |
| 77251 | SentenceChunker (`by_sentences`) | 33 | 591 | Tốt — không cắt giữa câu, nhưng chunk ngắn dễ mất bối cảnh mục |
| 77251 | RecursiveChunker (`recursive`) | 31 | 631 | Tốt nhất — bám ranh giới đoạn trước, chỉ hạ xuống câu khi cần |
| 77250 Chính sách vận chuyển | FixedSizeChunker (`fixed_size`) | 35 | 781 | Kém |
| 77250 | SentenceChunker (`by_sentences`) | 44 | 550 | Trung bình — nhiều chunk vụn ở phần bảng biểu |
| 77250 | RecursiveChunker (`recursive`) | 37 | 662 | Tốt |
| 77265 Giải quyết tranh chấp | FixedSizeChunker (`fixed_size`) | 7 | 765 | Kém |
| 77265 | SentenceChunker (`by_sentences`) | 10 | 485 | Trung bình |
| 77265 | RecursiveChunker (`recursive`) | 9 | 540 | Tốt |

> `fixed_size` luôn cho độ dài TB sát trần 800 vì nó cắt theo vị trí, không theo nội dung — đều đặn nhưng vô nghĩa về ngữ nghĩa. `recursive` cho số chunk gần `fixed_size` mà vẫn tôn trọng ranh giới đoạn, nên là điểm cân bằng tốt nhất trên corpus này.

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

**Thành viên 1 — Lê Anh Duy**
- **Loại chiến lược:** Recursive — `RecursiveChunker(chunk_size=800)` → 419 chunk / 7 tài liệu
- **Mô tả & lý do chọn cho chủ đề này:** Văn bản quy định Shopee được soạn theo đoạn và điều khoản đánh số, nên cắt theo ranh giới đoạn (dòng trống) trước rồi mới hạ dần xuống xuống-dòng đơn rồi tới dấu chấm, giữ được trọn vẹn một điều khoản trong một chunk. Chọn 800 ký tự vì baseline cho thấy mức này giữ độ dài TB ~630 mà vẫn không chẻ đôi điều khoản, trong khi `fixed_size` cắt cứng giữa câu và `by_sentences` sinh nhiều chunk vụn ở phần bảng biểu.
- **Code snippet (nếu custom):** dùng chunker có sẵn, không viết tuỳ chỉnh. Hai chỗ phải sửa để chạy được trên dữ liệu thật: đệ quy trên cả `buffer + separator + piece` thay vì chỉ `piece` (nếu không đầu mục `m.` thành chunk 1 ký tự), và thêm trần `max_chars` cho `SentenceChunker` vì corpus có "câu" dài 3025 ký tự do liệt kê bằng dấu chấm phẩy.

**Thành viên 2 — Nguyễn Thị Phương Duyên**
- **Loại chiến lược:** Sentence — `SentenceChunker(max_sentences_per_chunk=3)` → 573 chunk, dài TB 461
- **Mô tả & lý do chọn:** Tách câu bằng lookbehind giữ lại dấu câu, và quan trọng hơn là có thêm một nhánh **tách cả ở vị trí xuống dòng ngay sau dấu chấm**. Văn bản Shopee xuống dòng rất nhiều giữa các điều khoản nên nhánh này giúp chunk bám sát ranh giới mục — đây là khác biệt chính so với bản của Duy.
- **Code snippet:** `src/team_chunking/duyen-chunking.py`

**Thành viên 3 — Đào Trọng Khang**
- **Loại chiến lược:** Sentence → 579 chunk, dài TB 456
- **Mô tả & lý do chọn:** Cách tiếp cận gần giống Duyên nhưng khác ở chi tiết xử lý khoảng trắng, cho ra số chunk xấp xỉ mà điểm thấp hơn 1.
- **Code snippet:** `src/team_chunking/khang-chunking.py`

**Thành viên 4 — Lê Quang Thành**
- **Loại chiến lược:** Sentence → 616 chunk, dài TB 425
- **Mô tả & lý do chọn:** Dùng `re.split` với mẫu `[.!?]\s+` — cách trực tiếp nhất, nhưng **dấu câu bị nuốt mất** vì `re.split` không có capture group, nên mọi chunk kết thúc bằng câu cụt.
- **Code snippet:** `src/team_chunking/thanh-chunking.py` (bản gốc giữ tại `.bak`). Bản đầu có **2 lỗi**, Thành nhờ sửa rồi chạy lại:
  1. `re.split(r'[.!?]\s+')` **nuốt mất dấu câu** vì phần khớp bị loại bỏ → thêm lookbehind. Kết quả: 616 chunk câu cụt → 605 chunk trọn vẹn, **5/10 → 6/10** (Q2 từ 0 lên 1 điểm).
  2. `RecursiveChunker._split` **thiếu bước gom mảnh liền kề** → sinh 1820 chunk vụn. Thêm `buffer` gom tới sát `chunk_size`: **1820 → 414 chunk**, và chunk trùng khít với bản của 3 người còn lại (0 lần gọi API vì cache trúng hết) — bằng chứng rằng bản sửa đã đúng.

### So Sánh Giữa Các Thành Viên

> Mọi ô chạy trên **cùng corpus, cùng 5 câu hỏi, cùng store, cùng backend** (`gemini-embedding-001`, 768 chiều) — chỉ đổi đúng một biến là code chunking. Sinh bởi `scripts/run_team_benchmark.py`, kết quả đầy đủ trong `ket_qua_benchmark_nhom.txt`.

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| **Duyên** | Sentence (573 chunk) | **9/10** | Tách cả ở `
` sau dấu chấm nên bám ranh giới điều khoản; câu duy nhất đạt 2/2 ở Q2 | Mất 1 điểm ở Q5 vì chunk ngắn không phủ hết danh mục a–m |
| Khang | Sentence (579 chunk) | 8/10 | Gần Duyên, giữ được dấu câu | Kém Duyên 1 điểm ở Q2 |
| Duy | FixedSize (372 chunk) | 8/10 | Có overlap 80; cửa sổ rộng 800 gom trọn cả câu chủ đề lẫn danh sách | Cắt ngang giữa từ, chunk mở đầu cụt nghĩa |
| Duy | Sentence (450 chunk) | 7/10 | Có trần `max_chars` chặn chunk 3000 ký tự | Ít điểm tách hơn Duyên nên chunk to, loãng |
| **Cả 4 người** | Recursive (≈418 chunk) | 6/10 ở cả 4 | Ranh giới đoạn sạch nhất | **Không có overlap**; cắt ngay sau câu chủ đề làm danh sách mất ngữ cảnh |
| Duy | **Heading (498 chunk, tự viết)** | **5/10** | Câu duy nhất khiến Q3 lên 2/2 nhờ gắn lại tiêu đề vào mọi mảnh con | **Thấp nhất bảng**: 81% chunk dùng chung phần mở đầu, có tiêu đề lặp 16 lần → embedding bị kéo lại gần nhau, loãng tín hiệu riêng |
| Thành | Sentence (605 chunk, đã sửa) | 6/10 | Sau khi thêm lookbehind thì dấu câu được giữ, Q2 lên 1 điểm | Vẫn thiếu nhánh tách ở xuống dòng như Duyên nên kém 3 điểm; Q1 vẫn 0/2 |
| Cả 4 người | FixedSize | 8/10 ở cả 4 | — | Lab cho sẵn nên chunk giống hệt nhau từng ký tự |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> **Sentence bản của Duyên (9/10)**, nhưng bài học không nằm ở tên chiến lược mà ở chỗ **ranh giới rơi vào đâu**: sau khi sửa lỗi cho Thành, **cả bốn bản `recursive` đều cho đúng 6/10 và sinh ra gần như cùng một tập chunk**, trong khi bốn bản `sentence` trải từ 6 đến 9 — khác biệt là do implementation chứ không do thuật toán. Điều bất ngờ nhất là `FixedSize` cắt cứng giữa từ lại được 8/10, hơn cả `recursive` "cắt đúng ngữ nghĩa": ở Q3, `recursive` cắt ngay **sau** câu chủ đề "…yêu cầu trả hàng/hoàn tiền trong các trường hợp sau:" nên chunk chứa danh sách mất luôn câu nói nó là danh sách của cái gì, còn cửa sổ 800 ký tự của `FixedSize` tình cờ gom được cả hai. Nói cách khác, **cắt đúng ranh giới ngữ nghĩa mà tách tiêu đề khỏi nội dung nó giới thiệu thì vẫn là cắt sai** — đây chính là lý do chunker theo heading bắt buộc phải gắn lại tiêu đề vào từng mảnh con.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Mua hàng trên Shopee Mall, sau khi yêu cầu trả hàng được chấp thuận thì phải gửi trả sản phẩm trong bao nhiêu ngày? | **06 ngày lịch** kể từ ngày yêu cầu trả hàng/hoàn tiền được chấp thuận; phải đóng gói trong bao bì ban đầu và dán kèm Phiếu Trả Hàng. | `77262_2628_3865` — mục 1.2 |
| 2 | Hàng bị hư hại trong quá trình vận chuyển thì phải khiếu nại trong vòng bao nhiêu ngày? *(câu cần lọc metadata)* | Tùy đối tượng: **Người Bán** — hàng bị hư hại/không nguyên vẹn khi hoàn trả: **03 ngày**, hàng thất lạc khi hoàn trả: **07 ngày**, tính từ khi đơn cập nhật trạng thái chuyển hoàn thành công. **Người Mua** — gửi yêu cầu Trả hàng/Hoàn tiền trong **15 ngày** kể từ khi giao hàng thành công. | `77250_14001_14778` — mục D.1.b (seller) **vs** `77251` mục 3.2 (buyer) |
| 3 | Người mua được yêu cầu trả hàng/hoàn tiền trong những trường hợp nào? | 7 trường hợp: không nhận được hàng / không nhận đủ hàng / nhận phải **hàng giả, hàng nhái**; sản phẩm lỗi hoặc hư hại khi vận chuyển; người bán giao sai sản phẩm; hàng khác biệt rõ rệt so với mô tả; sản phẩm hết hạn sử dụng; người bán tự thỏa thuận đồng ý cho trả hàng; hàng còn nguyên vẹn nguyên bao bì nhưng người mua không còn nhu cầu (**Trả hàng COM**). | `77251_2180_3085` — mục 3.1 |
| 4 | Quy trình giải quyết tranh chấp của Shopee gồm mấy bước và Shopee đưa ra hướng giải quyết trong bao lâu? | **4 bước** (Bước 1 người mua tạo khiếu nại trong mục "Đơn Mua" → Bước 2 bộ phận khiếu nại tiếp nhận → Bước 3 xử lý theo Chính sách Trả hàng và Hoàn tiền, với tranh chấp khác thì đưa hướng giải quyết trong **07 ngày làm việc** kể từ khi nhận đủ thông tin/tài liệu → Bước 4 chuyển cơ quan nhà nước có thẩm quyền nếu vượt thẩm quyền của sàn). | `77265_907_2658` — mục 1, Bước 1–4 (bản sao: `77245_14121_15870`) |
| 5 | Những nội dung nào bị nghiêm cấm đăng bán trên Shopee? | Gồm: nội dung phản động, chống phá, bài xích tôn giáo, khiêu dâm, bạo lực, xâm phạm chủ quyền/an ninh quốc gia; thông tin rác làm mất uy tín dịch vụ Shopee; xúc phạm người khác; tuyên truyền điều pháp luật nghiêm cấm (heroin, thuốc lắc…); quảng cáo sản phẩm độc hại (thuốc lá, rượu, cần sa); văn hóa phẩm đồi trụy; **tài liệu bí mật quốc gia**, bí mật nhà nước, bí mật kinh doanh, bí mật cá nhân; … và các sản phẩm thuộc Danh sách cấm/hạn chế của Shopee. | `77246_1279_2847` — mục 2, điểm a–m (bản sao: `77245_52118_52876`) |

> Bộ câu hỏi máy đọc được: `data/shopee-ecommerce/gold.json` (sinh bởi `scripts/make_gold.py`), gồm cả chuỗi neo để chấm ở mức nội dung và `evidence` trích nguyên văn. Chunk định danh bằng `{doc_id}_{start}_{end}` thay vì `file#0` vì chỉ số chunk đổi theo chiến lược, còn offset thì cố định nên cả nhóm dùng chung một vùng gold.

> Câu 2 cần filter vì cố ý không nêu người hỏi là ai: 77250 (`seller`) và 77251 (`buyer`) cùng từ vựng "hư hại / khiếu nại / bồi thường" nhưng khác đáp án (03–07 ngày vs 15 ngày), không lọc thì top-3 lẫn cả hai và agent trả lời sai đối tượng.

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

> Cột "chiến lược tốt nhất" lấy từ bảng so sánh 11 ô ở mục 2 (4 thành viên × 3 chiến lược).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Shopee Mall gửi trả trong bao nhiêu ngày | Mọi chiến lược trừ Thành/sentence đều 2/2 | **Có**, ở top-1 (0.826) | Vùng gold nằm trọn trong 1 chunk |
| 2 | Hàng hư hại khiếu nại bao nhiêu ngày *(lọc)* | **Duyên/sentence (2/2)** — duy nhất | Chỉ với chunk đủ mịn | Câu khó nhất: 8/11 ô được 0 điểm |
| 3 | Trường hợp nào được trả hàng/hoàn tiền | fixed + sentence (2/2) | Có, trừ recursive | **Cả 3 bản recursive đều 0/2** — cắt ngay sau câu chủ đề |
| 4 | Quy trình tranh chấp mấy bước | Mọi chiến lược đều 2/2 | **Có**, ở top-1 (0.815) | Câu dễ nhất: 11/11 ô đạt điểm tối đa |
| 5 | Nội dung cấm đăng bán | fixed + recursive (2/2) | **Có** | Chunk `sentence` quá ngắn nên chỉ được 1/2 ở cả 3 bản |

**Điểm cao nhất của nhóm: 9/10** (Duyên / sentence). Bản của Lê Anh Duy: 8/10 với `fixed`, 7/10 với `sentence`, 6/10 với `recursive`.

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, ở câu 2 — A/B chứng minh rõ: **không lọc** thì top-3 toàn 77250 (`seller`, mốc 03/07 ngày), **lọc `audience=buyer`** thì top-3 chuyển hẳn sang 77251 (`buyer`, mốc 15 ngày). Cùng một câu hỏi, metadata quyết định người hỏi nhận về đáp án của ai; không lọc thì người mua nhận nhầm quy định dành cho người bán. Nhưng filter chỉ giải quyết được một nửa: nó chọn đúng *tài liệu* chứ không chọn đúng *đoạn*, nên câu 2 vẫn 0/2 vì trong chính 77251 thì mục 3.1 vẫn thắng mục 3.2.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1) **Cắt "đúng ngữ nghĩa" vẫn có thể là cắt sai**: cả 3 bản `recursive` đều 0/2 ở Q3 vì cắt ngay sau câu chủ đề, tách danh sách khỏi câu giới thiệu nó; `FixedSize` cắt cứng giữa từ lại được 2/2 nhờ cửa sổ rộng gom được cả hai. 2) **Cosine tuyệt đối vô nghĩa**: hai câu không liên quan (phí vận chuyển vs thời tiết) vẫn đạt 0.655 trong khi top-1 đúng chỉ 0.797 — chênh 0.14, không thể đặt ngưỡng, chỉ dùng được thứ hạng. 3) **Cùng tên chiến lược, khác người viết, khác 4 điểm**: `sentence` trải từ 5/10 đến 9/10 chỉ vì khác regex tách câu.

**Bài học rút ra khi so sánh trong nhóm:**
> `fixed` cho **kết quả giống hệt nhau ở cả 4 người** (8/10) vì lab cho sẵn — nó là mốc đối chứng chứng minh mọi chênh lệch còn lại đến từ code chứ không từ dữ liệu hay cách chấm. Bốn bản `recursive` viết độc lập cũng hội tụ về đúng 6/10 với gần như cùng tập chunk, trong khi bốn bản `sentence` trải từ 6 đến 9 — tức **ở `sentence` cách viết quan trọng hơn thuật toán**, còn ở `recursive` thì thuật toán quyết định. Đáng chú ý: sửa lỗi cho Thành chỉ nâng `sentence` được 1 điểm (5→6), cho thấy **giữ được dấu câu là điều kiện cần nhưng chưa đủ** — thứ tạo ra 3 điểm chênh với Duyên là nhánh tách thêm ở vị trí xuống dòng.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Thêm **overlap cho `recursive`** (hiện bằng 0) để điều khoản nằm sát ranh giới vẫn xuất hiện trọn trong ít nhất một chunk — đây là nguyên nhân trực tiếp của hai câu hỏng. Bổ sung metadata **cấp mục** (`section`, `clause_no`) chứ không chỉ cấp tài liệu, để lọc được tới đúng điều khoản thay vì chỉ tới đúng file; và khử trùng lặp `77245` với các tài liệu nó chép lại, vì hiện một nội dung tồn tại hai bản làm loãng bảng xếp hạng.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá | Căn cứ |
|----------|-------------------|--------|
| Lựa chọn tài liệu (Document Set Quality) | **10** / 10 | 7 tài liệu nguồn công khai, chủ đề rõ, đủ 7 trường metadata; `audience` gán có bằng chứng (đếm tần suất + trích văn bản) và tạo được cặp tài liệu cho câu hỏi cần lọc |
| Thiết kế chiến lược (Strategy Design) | **15** / 15 | Baseline 3 tài liệu × 3 chiến lược, bảng so sánh **13 ô** (4 thành viên × 3 chiến lược + `HeadingChunker` tự viết) đo trên cùng điều kiện. `HeadingChunker` tuy chỉ đạt 5/10 nhưng cho ra kết luận đáng giá nhất: chữa đúng failure case vẫn có thể làm tổng thể tệ đi |
| Chất lượng truy xuất (Retrieval Quality) | **9** / 10 | Điểm cao nhất nhóm 9/10; chấm 2 mức (giao khoảng + chuỗi neo) thay vì chỉ kiểm `doc_id`, có A/B chứng minh filter đổi hẳn tài liệu trả về |
| Thuyết trình (Demo) | **—** / 5 | Điền sau buổi demo |
| **Tổng phần nhóm** | **34 / 35** *(chưa tính demo)* | |
