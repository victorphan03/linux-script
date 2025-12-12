#!/bin/bash

# Kiểm tra quyền Root
if [ "$EUID" -ne 0 ]; then
  echo "Vui lòng chạy script bằng quyền root (sudo)"
  exit
fi

echo "=== CÀI ĐẶT SMB SHARE TỰ ĐỘNG ==="

# 1. Cập nhật và cài đặt Samba
echo "[1/5] Đang cài đặt Samba..."
apt update -qq
apt install samba -y -qq

# 2. Nhập thông tin cấu hình
echo ""
read -p "Nhập tên USER muốn dùng để đăng nhập SMB: " SMB_USER
read -s -p "Nhập MẬT KHẨU cho user này: " SMB_PASS
echo ""
read -p "Nhập tên thư mục chia sẻ (Ví dụ: data): " SHARE_NAME
SHARE_DIR="/srv/samba/$SHARE_NAME"

# 3. Tạo User và Thư mục
echo ""
echo "[2/5] Đang cấu hình User và Thư mục..."

# Tạo user hệ thống nếu chưa có (user ảo không đăng nhập shell)
if id "$SMB_USER" &>/dev/null; then
    echo "User $SMB_USER đã tồn tại trong hệ thống."
else
    useradd -M -s /sbin/nologin $SMB_USER
    echo "Đã tạo user hệ thống $SMB_USER."
fi

# Đặt mật khẩu Samba
echo -e "$SMB_PASS\n$SMB_PASS" | smbpasswd -a -s $SMB_USER

# Tạo thư mục và cấp quyền
mkdir -p "$SHARE_DIR"
chown -R $SMB_USER:$SMB_USER "$SHARE_DIR"
chmod 775 "$SHARE_DIR"

# 4. Cấu hình file smb.conf
echo "[3/5] Đang ghi cấu hình vào /etc/samba/smb.conf..."

# Backup file gốc
cp /etc/samba/smb.conf /etc/samba/smb.conf.bak

# Thêm cấu hình share vào cuối file
cat <<EOT >> /etc/samba/smb.conf

[$SHARE_NAME]
   path = $SHARE_DIR
   browseable = yes
   read only = no
   guest ok = no
   valid users = $SMB_USER
   create mask = 0775
   directory mask = 0775
EOT

# 5. Mở port và Khởi động lại
echo "[4/5] Cấu hình tường lửa và khởi động lại dịch vụ..."
ufw allow samba > /dev/null 2>&1
systemctl restart smbd

# Lấy IP máy
IP_ADDR=$(hostname -I | cut -d' ' -f1)

echo ""
echo "=== CÀI ĐẶT HOÀN TẤT ==="
echo "---------------------------------------------"
echo "Đường dẫn truy cập từ Windows: \\\\$IP_ADDR\\$SHARE_NAME"
echo "Đường dẫn truy cập từ MacOS:   smb://$IP_ADDR/$SHARE_NAME"
echo "Username: $SMB_USER"
echo "Password: (Đã ẩn)"
echo "---------------------------------------------"
