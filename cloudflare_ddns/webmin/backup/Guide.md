Ngữ cảnh và Vai trò:
Hãy đóng vai là một chuyên gia lập trình Perl và phát triển Webmin Module. Nhiệm vụ của bạn là viết mã nguồn hoàn chỉnh cho một Custom Webmin Module có tên là "Homelab Backup 3-2-1-1-0".
Module này đóng vai trò là giao diện đồ họa (GUI) trên Webmin để quản lý một kịch bản shell script sao lưu dữ liệu tập trung. Kịch bản này không chỉ sao lưu hệ thống Docker cục bộ mà còn có khả năng kết nối SSH/SCP để kéo dữ liệu từ các máy chủ khác (Remote Servers), sau đó ứng dụng MinIO Object Lock và Google Drive để lưu trữ.

Tổng quan Hệ thống Backup gốc (Luồng xử lý):
Hệ thống sao lưu tuân thủ quy tắc 3-2-1-1-0:

Tạo thư mục tạm (Temp Directory) trên máy chủ chính.

[Local Backup]: Plugin quét và liệt kê tất cả các Docker Compose project/stack trong thư mục nguồn (mặc định /home/x79). Người dùng chọn các stack cần backup trên giao diện Webmin. Khi backup, từng stack được chọn sẽ thực hiện độc lập: Dừng dịch vụ của riêng stack đó (docker compose stop) -> Nén toàn bộ thư mục dữ liệu stack -> Bật lại dịch vụ stack (docker compose start) ngay lập tức trước khi chuyển sang stack kế tiếp.

[Remote Backup]: Nếu có cấu hình máy chủ phụ, script kết nối qua SSH (dùng Public Key) để nén thư mục đích trên server phụ, sau đó dùng SCP tải file nén đó về thư mục tạm trên máy chủ chính, rồi xóa file nén tạm trên máy chủ phụ.

Kiểm tra tính toàn vẹn của tất cả các file nén (tar -tzf).

Dùng rclone đẩy tất cả file nén vào Bucket MinIO (đóng vai trò Immutable/Bất khả xâm phạm nhờ tính năng Object Lock).

Dùng rclone đẩy tiếp các file nén lên Google Drive (đóng vai trò Offsite).

Xóa các file backup cũ trên Google Drive theo cấu hình Retention policy và xóa toàn bộ file nén tạm ở máy chủ chính.

Gửi thông báo báo cáo chi tiết qua Mail (Bao gồm trạng thái của cả Local và Remote backup).

Yêu cầu Kiến trúc Webmin Module:
Module cần tương tác với kịch bản bash có sẵn thông qua một file cấu hình riêng biệt hoặc lưu trữ tham số trực tiếp trong hệ thống cấu hình của Webmin (/etc/webmin/homelab-backup/config).

Chi tiết các trang và tính năng cần lập trình:

Trang Dashboard chính (index.cgi):

Đọc và hiển thị trạng thái của lần chạy backup cuối cùng từ file log (/opt/backup_homelab.log).

Có nút "Run Backup Now" (Kích hoạt script chạy bằng giao diện loading).

Trang Cấu hình (Sử dụng config.info tiêu chuẩn của Webmin):
Tạo form nhập liệu được chia làm 3 phần rõ ràng:
Phần 1: Cấu hình Local & Cloud

Local Source Directory (mặc định: /home/x79).

Temp Directory (mặc định: /opt/backups/tmp).

MinIO Rclone Remote (mặc định: minio_local:homelab-backups/).

Cloud Rclone Remote (mặc định: remote_drive:Homelab_Backups/).

Cloud Retention days (mặc định: 7).
Phần 2: Cấu hình Remote Backup (SSH/SCP)

Enable Remote Backup? (Yes/No).

Remote Server IP.

Remote SSH Port (mặc định: 22).

Remote SSH User (mặc định: root).

Remote Source Directory (Thư mục cần backup trên server phụ).
Phần 3: Cấu hình Cảnh báo

Telegram Bot Token.

Telegram Chat ID.

Quản lý Lịch trình (Cron integration):

Tích hợp giao diện chọn giờ/ngày chạy script tự động.

Khi lưu, tạo hoặc cập nhật cron job của user root tương ứng với lịch đã chọn.

Trang Log Viewer (log.cgi):

Đọc và hiển thị nội dung file /opt/backup_homelab.log.

Có nút "Clear Log".

Yêu cầu về Đầu ra mã nguồn (Output requirements):
Hãy cung cấp cấu trúc thư mục của module và mã nguồn cho từng file quan trọng sau:

module.info (Thông tin metadata).

config.info (Định nghĩa form cấu hình Webmin).

homelab-backup-lib.pl (Thư viện chứa các hàm gọi system commands, đọc/ghi file).

index.cgi (Giao diện chính dùng thư viện UI của Webmin).

Kịch bản Bash gốc được tinh chỉnh để đọc các biến môi trường/cấu hình từ Webmin, có tích hợp khối lệnh IF để xử lý phần SSH/SCP nếu Remote Backup được bật (Giả định rằng SSH Key không mật khẩu đã được quản trị viên setup sẵn).

Vui lòng viết code bám sát thư viện webmin/web-lib.pl và ui-lib.pl, sử dụng giao diện Theme Authentic tiêu chuẩn của Webmin để UI hiển thị đẹp. Các thao tác gọi lệnh hệ thống cần chạy dưới quyền root.
