#!/bin/bash
# =================================================================
# Script tu dong cai dat va kich hoat update-dns.service
# =================================================================

# 1. Kiem tra quyen root
if [ "$EUID" -ne 0 ]; then
    echo "Loi: Vui long chay script voi quyen root (sudo bash install_service.sh)"
    exit 1
fi

echo "=========================================="
echo "  BAT DAU CAI DAT UPDATE-DNS SERVICE"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/root/update_dns"
SERVICE_NAME="update-dns.service"
SYSTEMD_PATH="/etc/systemd/system/$SERVICE_NAME"

# 2. Cai dat cac goi can thiet (jq, curl) neu chua co
echo "[1/6] Kiem tra va cai dat goi can thiet (jq, curl)..."
if ! command -v jq &> /dev/null || ! command -v curl &> /dev/null; then
    if command -v apt-get &> /dev/null; then
        apt-get update -y && apt-get install -y jq curl
    elif command -v yum &> /dev/null; then
        yum install -y jq curl
    elif command -v dnf &> /dev/null; then
        dnf install -y jq curl
    fi
else
    echo "  -> jq va curl da duoc cai dat."
fi

# 3. Tao thu muc dich /root/update_dns neu chua co va copy cac file script
echo "[2/6] Thiet lap thu muc $TARGET_DIR..."
mkdir -p "$TARGET_DIR"

if [ "$SCRIPT_DIR" != "$TARGET_DIR" ]; then
    echo "  -> Sao chep cac file script vao $TARGET_DIR..."
    cp -r "$SCRIPT_DIR"/* "$TARGET_DIR"/
fi

# 4. Phan quyen thuc thi cho tat ca cac file .sh
echo "[3/6] Phan quyen thuc thi (chmod +x) cho cac script..."
chmod +x "$TARGET_DIR"/*.sh

# 5. Copy file service vao /etc/systemd/system/
echo "[4/6] Cau hinh file service vao systemd..."
if [ -f "$TARGET_DIR/$SERVICE_NAME" ]; then
    cp "$TARGET_DIR/$SERVICE_NAME" "$SYSTEMD_PATH"
elif [ -f "$SCRIPT_DIR/$SERVICE_NAME" ]; then
    cp "$SCRIPT_DIR/$SERVICE_NAME" "$SYSTEMD_PATH"
else
    echo "Loi: Khong tim thay file $SERVICE_NAME!"
    exit 1
fi

# 6. Reload daemon, enable va start service
echo "[5/6] Khoi dong va kich hoat service..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

# 7. Kiem tra trang thai
echo "[6/6] Kiem tra trang thai service..."
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "=========================================="
    echo "  THANH CONG! Service da duoc kich hoat."
    echo "=========================================="
    echo "Cac lenh quan ly thuong dung:"
    echo "  - Xem trang thai: systemctl status $SERVICE_NAME"
    echo "  - Xem log truc tiep: tail -f /var/log/update-dns.log"
    echo "  - Khoi dong lai:  systemctl restart $SERVICE_NAME"
    echo "  - Dung service:   systemctl stop $SERVICE_NAME"
else
    echo "Canh bao: Service chua khoi dong thanh cong. Kiem tra log:"
    systemctl status "$SERVICE_NAME" --no-pager
fi
