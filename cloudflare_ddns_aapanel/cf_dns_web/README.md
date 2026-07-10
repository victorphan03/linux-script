# Cloudflare DNS Web App

Đây là một ứng dụng Web độc lập (Standalone) giúp bạn tự động cập nhật địa chỉ IP động cho tên miền trên Cloudflare, hoạt động liên tục 24/7 ở chế độ nền. Ứng dụng này thay thế hoàn toàn cho các Bash Script truyền thống.

## 🌟 Tính năng nổi bật
- **Giao diện Quản trị**: Bảng điều khiển siêu mượt (Premium Dark Mode) giúp bạn dễ dàng quản lý (Thêm/Sửa/Nhân bản/Xóa) hàng loạt cấu hình tên miền ngay trên trình duyệt.
- **Tiến trình hợp nhất**: Vòng lặp cập nhật (Background Daemon) được nhúng gọn nhẹ bên trong máy chủ Node.js, không cần tạo ra nhiều script độc lập trên Linux gây lãng phí tài nguyên.
- **Thiết lập thời gian linh hoạt**: Cho phép chỉnh sửa thời gian quét IP (VD: Quét mỗi 30 giây) ngay trên trang chủ.
- **Force Update**: Nút cho phép bạn ép hệ thống gọi API Cloudflare ngay lập tức để kiểm tra trạng thái hoạt động.

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy

Dự án này sử dụng trình quản lý **PM2** để tiến trình có thể chạy ẩn 24/7 và tự khởi động cùng hệ thống.

### 1. Chuẩn bị
Máy của bạn cần phải được cài đặt Node.js trước khi bắt đầu.

### 2. Sử dụng công cụ Quản lý (`manager.sh`)
Để tiết kiệm thời gian, một script quản lý tên là `manager.sh` đã được tích hợp sẵn trong thư mục dự án.

Bạn mở Terminal, di chuyển vào thư mục dự án và chạy các lệnh sau:

- **Khởi động ứng dụng lần đầu (hoặc chạy lại)**:
  ```bash
  cd /home/x79/linux-script/cf_dns_web
  ./manager.sh start
  ```
  *(Lệnh này sẽ tự động kiểm tra và cài đặt PM2 nếu máy bạn chưa có, sau đó khởi chạy Web App)*

- **Các lệnh quản lý khác:**
  - `./manager.sh restart`   - Khởi động lại ứng dụng.
  - `./manager.sh stop`      - Dừng tiến trình chạy ngầm.
  - `./manager.sh status`    - Xem trạng thái đang chạy của tiến trình (RAM/CPU đang dùng).
  - `./manager.sh logs`      - Xem nhật ký hoạt động ngầm để biết hệ thống đang cập nhật IP ra sao.
  - `./manager.sh startup`   - Tạo Service để ứng dụng **tự động khởi chạy cùng Linux** mỗi khi mất điện hoặc Reboot.

### 3. Truy cập Giao diện Web
Sau khi khởi động thành công bằng `./manager.sh start`, bạn hãy mở trình duyệt và truy cập vào địa chỉ:
👉 **`http://<IP_MAY_CHU_CUA_BAN>:3000`**

(Ví dụ: `http://localhost:3000` hoặc `http://192.168.1.100:3000`).

Tại đây, bạn chỉ việc bấm nút "Thêm Cấu Hình" để điền Email và API Key của Cloudflare.

---

## 🛠️ Cấu trúc Dữ liệu
Toàn bộ thông tin cài đặt và danh sách tên miền của bạn được lưu an toàn dưới dạng file JSON tĩnh tại thư mục `data/`:
- `data/configs.json`: Nơi chứa danh sách tên miền.
- `data/settings.json`: Nơi chứa thông số độ trễ (Sleep Interval).
*(Chỉ cần sao lưu thư mục `data/` này là bạn có thể di chuyển cấu hình sang bất kỳ máy chủ nào khác)*
