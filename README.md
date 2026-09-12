# Cổng ANTT Ấp Bình Châu – V2

Bản V2 nâng cấp từ bản bạn đang chạy.

## Đã thêm
- Tên và nhận diện **Ấp Bình Châu**.
- Dùng ảnh logo/biểu trưng bạn cung cấp.
- Mã phản ánh tự động: `ANTT-2026-0001`.
- Mã lịch hẹn tự động: `LICH-2026-0001`.
- Mức độ phản ánh: Bình thường / Cần xử lý / Khẩn cấp.
- Đính kèm ảnh/video tối đa 50 MB.
- Chọn vị trí trên bản đồ hoặc dùng vị trí hiện tại.
- Dashboard Ban ấp với thống kê.
- Tương thích dữ liệu SQLite của bản V1: dữ liệu cũ được giữ lại và tự bổ sung trường mới.

## Chạy trên Windows

Mở CMD trong thư mục dự án:

```bat
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
py app.py
```

Mở Chrome:
http://127.0.0.1:5000

## Quản trị demo
- Địa chỉ: http://127.0.0.1:5000/admin
- Tài khoản: admin
- Mật khẩu: admin123

## Lưu ý
Đây vẫn là bản thử nghiệm/MVP. Trước khi đưa lên Internet cần đổi mật khẩu, secret key, bật HTTPS, phân quyền, chống spam, sao lưu dữ liệu và có quy trình bảo vệ dữ liệu cá nhân.
