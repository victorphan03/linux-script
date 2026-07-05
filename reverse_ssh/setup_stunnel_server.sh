#!/bin/bash

# ==============================================================================
# Script: setup_stunnel_server.sh
# Mô tả: Cấu hình Stunnel Server trên Máy A (Nginx Server)
# ==============================================================================

if [ "$EUID" -ne 0 ]; then
  echo "Vui lòng chạy script với quyền root (sudo)"
  exit 1
fi

echo "=== Cài đặt Stunnel4 và OpenSSL ==="
if command -v apt-get &> /dev/null; then
    apt-get update && apt-get install -y stunnel4 openssl
elif command -v yum &> /dev/null; then
    yum install -y epel-release && yum install -y stunnel openssl
else
    echo "Không tìm thấy trình quản lý gói phù hợp. Vui lòng cài đặt stunnel4 thủ công."
    exit 1
fi

echo "=== Cấu hình Stunnel Server ==="
read -p "Nhập port Stunnel sẽ lắng nghe trên mạng public (Mặc định: 8443): " STUNNEL_PORT
STUNNEL_PORT=${STUNNEL_PORT:-8443}

CERT_PATH="/etc/stunnel/stunnel.pem"
if [ ! -f "$CERT_PATH" ]; then
    echo "Đang tạo chứng chỉ SSL Self-signed tại $CERT_PATH..."
    openssl req -new -x509 -days 3650 -nodes -out $CERT_PATH -keyout $CERT_PATH -subj "/C=VN/ST=HCM/L=HCM/O=IT/CN=stunnel.server"
    chmod 600 $CERT_PATH
fi

CONF_PATH="/etc/stunnel/stunnel.conf"
echo "Đang tạo cấu hình Stunnel tại $CONF_PATH..."

cat > "$CONF_PATH" <<EOF
cert = $CERT_PATH
pid = /var/run/stunnel.pid

[ssh]
accept = $STUNNEL_PORT
connect = 127.0.0.1:22
EOF

# Kích hoạt stunnel tự động chạy
if [ -f "/etc/default/stunnel4" ]; then
    sed -i 's/ENABLED=0/ENABLED=1/g' /etc/default/stunnel4
fi

systemctl enable stunnel4
systemctl restart stunnel4

echo "=== ĐÃ HOÀN TẤT TRÊN MÁY A ==="
echo "Stunnel Server đang lắng nghe ở port $STUNNEL_PORT và chuyển tiếp vào 127.0.0.1:22 (SSH)."
echo "Trạng thái:"
systemctl status stunnel4 --no-pager
echo ""
echo "=> Tiếp theo, hãy sang Máy B và chạy script cài đặt Client."
