#!/bin/bash
# =================================================================
# Script cai dat update-dns thanh Systemd Service
# =================================================================

if [ "$EUID" -ne 0 ]; then
    echo "Loi: Vui long chay voi quyen root: sudo bash install.sh"
    exit 1
fi

echo "=========================================="
echo "    BAT DAU CAI DAT UPDATE-DNS SERVICE"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DNS_SCRIPT="$SCRIPT_DIR/update-dns.sh"
SERVICE_FILE="/etc/systemd/system/update-dns.service"

# 1. Kiem tra file update-dns.sh
if [ ! -f "$DNS_SCRIPT" ]; then
    echo "Loi: Khong tim thay $DNS_SCRIPT!"
    exit 1
fi

chmod +x "$DNS_SCRIPT"

# 2. Cai dat cac goi can thiet
echo "[1/4] Kiem tra va cai dat jq, curl..."
if ! command -v jq &> /dev/null || ! command -v curl &> /dev/null; then
    if command -v apt-get &> /dev/null; then
        apt-get update -y && apt-get install -y jq curl
    elif command -v yum &> /dev/null; then
        yum install -y jq curl
    elif command -v dnf &> /dev/null; then
        dnf install -y jq curl
    fi
fi

# 3. Tao file service systemd
echo "[2/4] Tao file systemd service tai $SERVICE_FILE..."
cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Tu dong cap nhat Cloudflare Dynamic DNS moi 30s
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$SCRIPT_DIR
ExecStart=/bin/bash $DNS_SCRIPT loop
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# 4. Kich hoat va khoi dong service
echo "[3/4] Kich hoat va khoi dong service..."
systemctl daemon-reload
systemctl enable update-dns.service
systemctl restart update-dns.service

# 5. Kiem tra trang thai
echo "[4/4] Kiem tra trang thai..."
sleep 2

if systemctl is-active --quiet update-dns.service; then
    echo "=========================================="
    echo "  THANH CONG! Service da duoc kich hoat."
    echo "=========================================="
    echo "Lenh quan ly:"
    echo "  - Xem trang thai: systemctl status update-dns.service"
    echo "  - Xem log:        journalctl -u update-dns.service -f"
    echo "  - Go cai dat:     sudo bash uninstall.sh"
else
    echo "Canh bao: Service chua khoi dong duoc. Kiem tra log:"
    systemctl status update-dns.service --no-pager
fi
