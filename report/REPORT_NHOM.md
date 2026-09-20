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

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| | FixedSizeChunker (`fixed_size`) | | | |
| | SentenceChunker (`by_sentences`) | | | |
| | RecursiveChunker (`recursive`) | | | |

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

**Thành viên 1 — [Tên]**
- **Loại chiến lược:** [FixedSize / Sentence / Recursive / custom]
- **Mô tả & lý do chọn cho chủ đề này:** *(2-3 câu)*
- **Code snippet (nếu custom):**
```python
# Dán mã nguồn (implementation) vào đây
```

**Thành viên 2 — [Tên]**
- **Loại chiến lược:**
- **Mô tả & lý do chọn:**
- **Code snippet (nếu custom):**

**Thành viên 3 — [Tên]**
- **Loại chiến lược:**
- **Mô tả & lý do chọn:**
- **Code snippet (nếu custom):**

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| | | | | |
| | | | | |
| | | | | |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> *Viết 2-3 câu — đây là phần được đánh giá cao nhất (khả năng suy nghĩ & giải thích):*

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

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> *Viết 2-3 câu:*

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> *Liệt kê 2-3 ý:*

**Bài học rút ra khi so sánh trong nhóm:**
> *Viết 2-3 câu — cùng tài liệu nhưng chiến lược khác nhau dẫn tới khác biệt gì?*

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> *Viết 2-3 câu:*

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | / 10 |
| Thiết kế chiến lược (Strategy Design) | / 15 |
| Chất lượng truy xuất (Retrieval Quality) | / 10 |
| Thuyết trình (Demo) | / 5 |
| **Tổng phần nhóm** | **/ 40** |
