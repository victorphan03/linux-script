#!/bin/bash

# ==============================================================================
# Script: uninstall_stunnel_server.sh
# Mô tả: Gỡ cài đặt hoàn toàn Stunnel Server đã được cài từ setup_stunnel_server.sh
# ==============================================================================

if [ "$EUID" -ne 0 ]; then
  echo "Vui lòng chạy script với quyền root (sudo)"
  exit 1
fi

echo "=== Đang dừng service stunnel4 ==="
systemctl stop stunnel4
systemctl disable stunnel4

echo "=== Đang xóa các file cấu hình và chứng chỉ ==="
rm -f /etc/stunnel/stunnel.conf
rm -f /etc/stunnel/stunnel.pem

if [ -f "/etc/default/stunnel4" ]; then
    echo "Đang khôi phục /etc/default/stunnel4..."
    sed -i 's/ENABLED=1/ENABLED=0/g' /etc/default/stunnel4
fi

echo "=== Đang gỡ bỏ gói phần mềm stunnel ==="
if command -v apt-get &> /dev/null; then
    apt-get remove --purge -y stunnel4
    apt-get autoremove -y
elif command -v yum &> /dev/null; then
    yum remove -y stunnel
else
    echo "[!] Không tìm thấy apt-get hoặc yum để gỡ cài đặt phần mềm."
fi

echo "=== HOÀN TẤT ==="
echo "Đã gỡ cài đặt Stunnel Server khỏi hệ thống."
