# Kết quả benchmark của từng thành viên

Mỗi file là output của `bench.py` chạy trên code chunking của chính người đó,
với chiến lược `sentence` (chiến lược mỗi bạn đã chọn).

| File | Người | Điểm |
|---|---|---|
| `ket_qua_benchmark_duy.txt` | Lê Anh Duy | 6/10 (`recursive` — chiến lược Duy chọn) |
| `ket_qua_benchmark_duyen.txt` | Nguyễn Thị Phương Duyên | **9/10** |
| `ket_qua_benchmark_khang.txt` | Đào Trọng Khang | 8/10 |
| `ket_qua_benchmark_thanh.txt` | Lê Quang Thành | 6/10 (sau khi sửa 2 lỗi theo yêu cầu) |

**CP6 yêu cầu mỗi người nộp `ket_qua_benchmark.txt` trong repo của mình.** Các
bạn tải file của mình về, đổi tên thành `ket_qua_benchmark.txt` và đặt ở thư
mục gốc repo cá nhân.

Tự chạy lại (cần API key Gemini trong `.env`):

```bash
python scripts/build_index.py --strategy sentence --provider gemini
python bench.py --strategy sentence --provider gemini > ket_qua_benchmark.txt
```

Bảng so sánh cả nhóm là artifact riêng: `ket_qua_benchmark_nhom.txt`, sinh bởi
`python scripts/run_team_benchmark.py --provider gemini`.
