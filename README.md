# Irrelevant Image Checker (Level 0 & 1) 🕵️‍♂️📷

Hệ thống backend Python FastAPI để kiểm tra ảnh "không liên quan" (irrelevant) dựa trên chất lượng và nội dung cơ bản.

## 🏗 Cấu trúc Project

```
.
├── app/
│   ├── main.py            # FastAPI entry point
│   ├── config.py          # Cấu hình ngưỡng kiểm tra
│   └── pipeline/
│       ├── level0.py      # Lọc chất lượng (Blur, Brightness, Size)
│       ├── level1.py      # Lọc nội dung (Text-heavy, Document-like)
│       └── common.py      # Tiện ích xử lý ảnh
├── ui/
│   └── index.html         # Giao diện test đơn giản
├── uploads/               # Thư mục lưu ảnh upload (tự tạo)
├── requirements.txt
└── README.md
```

## 🚀 Cài đặt & Chạy

### 1. Cài đặt môi trường
Yêu cầu Python 3.8+.
```bash
pip install -r requirements.txt
```
*(Lưu ý: Để `pytesseract` hoạt động tốt nhất, bạn cần cài đặt [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) trên máy và thêm vào PATH. Tuy nhiên hệ thống sẽ tự động fallback nếu không tìm thấy tesseract.)*

### 2. Chạy Server
```bash
uvicorn app.main:app --reload
```
Server sẽ chạy tại `http://127.0.0.1:8000`.

### 3. Test hệ thống
- Mở trình duyệt truy cập: `http://127.0.0.1:8000/ui/`
- Hoặc dùng API trực tiếp:
  - `POST /api/check-image` (multipart/form-data)
  - `GET /healthz` (Health check)

## ⚙️ Cấu hình Ngưỡng (Thresholds)
Chỉnh sửa trong `app/config.py`:

| Tham số | Giá trị mặc định | Giải thích |
|---------|------------------|------------|
| `BLUR_THRESHOLD` | 100.0 | Variance of Laplacian. < 100 là ảnh mờ (HARD_BLOCK). |
| `DARK_THRESHOLD` | 50.0 | Độ sáng trung bình < 50 (SOFT_BLOCK). |
| `BRIGHT_THRESHOLD` | 200.0 | Độ sáng trung bình > 200 (SOFT_BLOCK). |
| `MIN_SHORT_SIDE_PX` | 400 | Cạnh ngắn nhất phải >= 400px. |
| `TEXT_SCORE_THRESHOLD` | 0.3 | Tỉ lệ text/cạnh > 0.3 là text-heavy (SOFT_BLOCK). |
| `DOC_SCORE_THRESHOLD` | 0.5 | Điểm giống tài liệu > 0.5 (HARD_BLOCK). |

### 💡 Gợi ý cho App Du Lịch
Với app du lịch, người dùng thường chụp cảnh, selfie, đồ ăn.
- **Blur**: Có thể giảm `BLUR_THRESHOLD` xuống `50-60` vì ảnh chụp vội có thể hơi rung nhưng vẫn chấp nhận được.
- **Brightness**: Nới lỏng `DARK_THRESHOLD` xuống `30` (chụp đêm) và `BRIGHT_THRESHOLD` lên `230` (chụp biển nắng gắt).
- **Text**: Giữ nguyên hoặc tăng nhẹ, vì khách có thể chụp vé tàu/xe (cần cân nhắc policy có cho phép up vé không).
- **Document**: Giữ chặt để tránh user up nhầm CCCD/Passport lên feed công khai.

## 🧪 Quy tắc Decision (Pipeline)

1. **Level 0 (Quality Check)**
   - ❌ **HARD_BLOCK**: Ảnh lỗi, quá nhỏ, quá mờ. => **DỪNG NGAY**.
   - ⚠️ **SOFT_BLOCK**: Ảnh tối/sáng quá, dung lượng nhỏ. => **GHI NHẬN LỖI, TIẾP TỤC**.

2. **Level 1 (Content Check)**
   - ⚠️ **SOFT_BLOCK**: Ảnh nhiều chữ (Screenshot/Meme).
   - ❌ **HARD_BLOCK**: Ảnh giống tài liệu văn bản (Document).

-> **Kết quả cuối cùng**:
- Nếu có bất kỳ `HARD_BLOCK` nào => **HARD_BLOCK**.
- Nếu không có HARD nhưng có `SOFT_BLOCK` => **SOFT_BLOCK** (Cần người duyệt hoặc warn user).
- Còn lại => **ALLOW**.
