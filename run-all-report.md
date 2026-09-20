# Số liệu để viết `REPORT_CANHAN.md` — nhóm ColdBrew

Duy đã chạy benchmark giúp cả nhóm (mình có API key Gemini). File này chứa **số
liệu của riêng bạn** để dán vào báo cáo cá nhân, cộng phần dữ kiện chung mà cả
nhóm phải khớp nhau.

Code chunking là **của chính bạn** — mình chỉ chạy, không sửa một dòng nào.

---

## 1. Điều kiện chạy (giống hệt nhau cho cả 4 người)

| | |
|---|---|
| Corpus | 7 tài liệu chính sách Shopee, `data/shopee-ecommerce/` |
| Bộ câu hỏi | 5 câu trong `data/shopee-ecommerce/gold.json` |
| Embedding | `gemini-embedding-001`, 768 chiều, `task_type` = `RETRIEVAL_DOCUMENT` cho chunk / `RETRIEVAL_QUERY` cho câu hỏi |
| Store & cách chấm | `src/store.py` của Duy — vì các bạn chỉ nộp phần chunking |
| Tham số | `fixed`: size 800 overlap 80 · `sentence`: 3 câu/chunk · `recursive`: size 800 |

Chỉ **một biến** thay đổi giữa các ô: code chunking của từng người.

**Cách chấm (2 điểm/câu, theo `docs/SCORING.md`):**
- 2đ — chunk gold ở top-1 **và** ngữ cảnh top-3 chứa chuỗi neo
- 1đ — chunk gold ở top-2/3
- 0đ — chunk gold vắng khỏi top-3

Chấm 2 mức vì tài liệu `77245` chép lại nguyên khối nội dung của `77246` và
`77265`; chỉ kiểm `doc_id` là chấm oan, nên phải kiểm cả chuỗi đặc trưng có
thật sự nằm trong ngữ cảnh không.

---

## 2. Kết quả của bạn

### Đào Trọng Khang — `SentenceChunker`, 579 chunk, dài TB 456 → **8/10**

| # | Câu hỏi | Top-1 chunk | Score | Liên quan? | Điểm |
|---|---|---|---|---|---|
| Q1 | Shopee Mall gửi trả trong bao nhiêu ngày | `77262_2637_3356` | 0.825 | Có | 2/2 |
| Q2 | Hàng hư hại khiếu nại bao nhiêu ngày *(lọc `audience=buyer`)* | `77251_2142_3082` | 0.693 | Không | 1/2 |
| Q3 | Trường hợp nào được trả hàng/hoàn tiền | `77251_2142_3082` | 0.795 | Có | 2/2 |
| Q4 | Quy trình tranh chấp mấy bước | `77245_14704_15247` | 0.815 | Có | 2/2 |
| Q5 | Nội dung cấm đăng bán | `77246_1282_1669` | 0.821 | Có | 1/2 |

Chiến lược khác của bạn: `fixed` 8/10 · `recursive` 6/10.

### Nguyễn Thị Phương Duyên — `SentenceChunker`, 573 chunk, dài TB 461 → **9/10** (cao nhất nhóm)

| # | Câu hỏi | Top-1 chunk | Score | Liên quan? | Điểm |
|---|---|---|---|---|---|
| Q1 | Shopee Mall gửi trả trong bao nhiêu ngày | `77262_2387_3035` | 0.813 | Có | 2/2 |
| Q2 | Hàng hư hại khiếu nại bao nhiêu ngày *(lọc `audience=buyer`)* | `77251_2185_3087` | 0.693 | Có | 2/2 |
| Q3 | Trường hợp nào được trả hàng/hoàn tiền | `77251_2185_3087` | 0.805 | Có | 2/2 |
| Q4 | Quy trình tranh chấp mấy bước | `77245_14802_15470` | 0.820 | Có | 2/2 |
| Q5 | Nội dung cấm đăng bán | `77246_1397_1756` | 0.819 | Có | 1/2 |

Chiến lược khác của bạn: `fixed` 8/10 · `recursive` 6/10.
Bạn là người **duy nhất** ăn trọn 2/2 ở Q2 — câu khó nhất, 8/11 ô còn lại được 0 điểm.

### Lê Quang Thành — `SentenceChunker`, 616 chunk, dài TB 425 → **5/10**

| # | Câu hỏi | Top-1 chunk | Score | Liên quan? | Điểm |
|---|---|---|---|---|---|
| Q1 | Shopee Mall gửi trả trong bao nhiêu ngày | `77262_1809_2431` | 0.822 | Không | 0/2 |
| Q2 | Hàng hư hại khiếu nại bao nhiêu ngày *(lọc `audience=buyer`)* | `77251_2142_3079` | 0.696 | Không | 0/2 |
| Q3 | Trường hợp nào được trả hàng/hoàn tiền | `77251_2142_3079` | 0.792 | Có | 2/2 |
| Q4 | Quy trình tranh chấp mấy bước | `77245_14802_15467` | 0.821 | Có | 2/2 |
| Q5 | Nội dung cấm đăng bán | `77245_51935_52319` | 0.818 | Có | 1/2 |

Chiến lược khác của bạn: `fixed` 8/10 · `recursive` **chưa chạy**.

`RecursiveChunker` của bạn sinh **1820 chunk** — gấp hơn 4 lần của người khác
(≈418). Nguyên nhân: `_split` đệ quy xuống nhưng **không gom các mảnh nhỏ liền
kề lại**, nên sinh ra hàng nghìn chunk vụn. Embed 1820 chunk vượt hạn mức free
tier nên mình dừng lại — nhưng con số này nên đưa vào báo cáo, nó đúng là dòng
*"Chunk vụn 5–10 ký tự → RecursiveChunker thiếu bước gom"* trong bảng lỗi
thường gặp của lab.

---

## 3. Dán gì vào đâu trong `REPORT_CANHAN.md`

**Mục 5 — Kết quả truy xuất (10 điểm):** dùng thẳng bảng của bạn ở trên.
Câu *"Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?"* → đếm số dòng
có điểm ≥ 1.

**Mục 2 — Hướng tiếp cận (10 điểm):** phần này **chỉ bạn viết được**, mình
không viết hộ. Gợi ý bám vào chính code của bạn: regex nào để tách câu, xử lý
được ca ngoại lệ nào (viết tắt `TS.`, số thập phân `1.5`, URL, đánh số điều
khoản `3.1.`), và ca nào biết là chưa xử lý được — **nêu ra được đánh giá cao
hơn giấu đi**.

**Mục 3 — Kết quả test (30 điểm):** phải là output `pytest tests/ -v` chạy trên
**máy của bạn, code của bạn**. Con số này mình không chạy hộ được vì các bạn
nộp repo riêng.

**Mục 1 và 4 (warm-up, dự đoán similarity):** tự làm, mỗi người một đáp án.

---

## 4. Dữ kiện chung — phải khớp giữa 4 báo cáo

Bộ 5 câu hỏi và đáp án chuẩn nằm trong `data/shopee-ecommerce/gold.json`,
và mục 3 của `REPORT_NHOM.md`. **Đừng tự đổi câu hỏi**, nếu không điểm giữa
các bạn không so được với nhau.

Câu **Q2 là câu cần lọc metadata**: nó cố ý không nêu người hỏi là ai, mà
`77250` (audience=`seller`) và `77251` (audience=`buyer`) dùng gần như cùng bộ
từ vựng nhưng **cho ra đáp án khác nhau** (03/07 ngày so với 15 ngày). Bằng
chứng A/B:

```
KHÔNG lọc          → top-3 toàn 77250 (seller), ra mốc 03/07 ngày
CÓ lọc buyer       → top-3 toàn 77251 (buyer),  ra mốc 15 ngày
```

Không lọc thì **người mua nhận về đáp án dành cho người bán**.

---

## 5. Tự chạy lại trên máy mình

Nếu bạn có API key Gemini (`aistudio.google.com/apikey` — free, không cần thẻ),
đặt vào `.env` rồi chạy đúng 2 lệnh:

```bash
python scripts/build_index.py --strategy sentence --provider gemini
python bench.py               --strategy sentence --provider gemini
```

Đổi `--strategy` thành `fixed` hoặc `recursive` để thử chiến lược khác.

Vài điều đã va phải, nói trước để đỡ mất thời gian:

- **Free tier giới hạn 1000 request/ngày, và 100/phút.** Quota tính theo **số
  văn bản**, không theo token — gộp 100 chunk vào một lời gọi vẫn bị tính 100.
  Batch API (tính theo token) bị chặn ở free tier.
- Vì vậy code có **cache `.npz`** (`data/embedding_cache.npz`) ghi sau mỗi lô:
  chạy lại lần hai gần như tức thì, không gọi API.
- Nhiều key thì khai `GEMINI_API_KEYS=key1,key2,key3` trong `.env`, code tự
  xoay vòng khi đụng giới hạn. Mỗi key phải thuộc **project khác nhau** mới có
  hạn mức riêng.
- **Không trộn được hai backend**: vector Gemini và vector model local nằm ở
  hai không gian khác nhau, so điểm giữa chúng là vô nghĩa.

Muốn xem lại chunk của mình trông ra sao thì mở
`data/index/<tên-bạn>-chunking/<chiến-lược>/chunks.jsonl` — mỗi dòng một chunk
kèm metadata, đọc bằng mắt được. Định danh chunk là `{doc_id}_{start}_{end}`
(offset ký tự trên phần thân tài liệu, sau khi bỏ frontmatter) nên đối chiếu
được trực tiếp với vùng gold trong `gold.json`.

---

## 6. Phát hiện chung, dùng cho phần thuyết trình

1. **`fixed` cho đúng 8/10 ở cả 4 người** — vì lab cho sẵn nên chunk giống hệt
   nhau từng ký tự. Nó thành mốc đối chứng: mọi chênh lệch còn lại đến từ code
   chứ không từ dữ liệu hay cách chấm.
2. **Ba bản `recursive` viết độc lập đều ra đúng 6/10**, trong khi bốn bản
   `sentence` trải từ 5 tới 9 điểm. Ở `sentence` thì cách viết quan trọng hơn
   thuật toán; ở `recursive` thì ngược lại.
3. **Cắt "đúng ngữ nghĩa" vẫn có thể là cắt sai.** Ở Q3, cả ba bản `recursive`
   đều 0/2 vì cắt ngay **sau** câu chủ đề *"…yêu cầu trả hàng/hoàn tiền trong
   các trường hợp sau:"* — chunk chứa danh sách mất luôn câu nói nó là danh
   sách của cái gì. `FixedSize` cắt cứng giữa từ lại được 2/2 nhờ cửa sổ 800 ký
   tự tình cờ gom được cả hai.
4. **Giá trị cosine tuyệt đối vô nghĩa**: hai câu hoàn toàn không liên quan
   (phí vận chuyển vs thời tiết) vẫn đạt 0.655, trong khi top-1 đúng của
   benchmark chỉ 0.797 — chênh vỏn vẹn 0.14. Không thể đặt ngưỡng, chỉ dùng
   được thứ hạng tương đối.
