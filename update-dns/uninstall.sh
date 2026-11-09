#!/bin/bash
# =================================================================
# Script go bo update-dns service khoi he thong
# =================================================================

show_help() {
    echo "=================================================================="
    echo " Go bo Update DNS Service khoi he thong"
    echo "=================================================================="
    echo "Cach dung:"
    echo "  sudo bash uninstall.sh [TUY_CHON]"
    echo ""
    echo "Tuy chon:"
    echo "  -h, --help    Hien thi huong dan su dung nay"
    echo ""
    echo "Chuc nang:"
    echo "  - Dung va vo hieu hoa service update-dns.service"
    echo "  - Xoa file cau hinh /etc/systemd/system/update-dns.service"
    echo "  - Reload systemd daemon de lam sach he thong"
    echo "=================================================================="
    exit 0
}

if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    show_help
fi

if [ "$EUID" -ne 0 ]; then
    echo "Loi: Vui long chay voi quyen root: sudo bash uninstall.sh"
    echo "Chay 'bash uninstall.sh -h' de xem huong dan."
    exit 1
fi

echo "=========================================="
echo "    BAT DAU GO CAI DAT UPDATE-DNS SERVICE"
echo "=========================================="

SERVICE_NAME="update-dns.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"

# 1. Dung service neu dang chay
echo "[1/3] Dung service $SERVICE_NAME..."
systemctl stop "$SERVICE_NAME" 2>/dev/null

# 2. Vo hieu hoa service
echo "[2/3] Vo hieu hoa (disable) service..."
systemctl disable "$SERVICE_NAME" 2>/dev/null

# 3. Xoa file service va reload systemd
echo "[3/3] Xoa file service va cap nhat systemd..."
if [ -f "$SERVICE_FILE" ]; then
    rm -f "$SERVICE_FILE"
fi

systemctl daemon-reload
systemctl reset-failed 2>/dev/null

echo "=========================================="
echo "  HOAN TAT! Da go bo update-dns.service."
echo "=========================================="
