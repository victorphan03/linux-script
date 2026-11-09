#!/bin/bash
# =================================================================
# CAU HINH (SUA THONG TIN CUA BAN TAI DAY)
# =================================================================

# 1. Email tai khoan Cloudflare
AUTH_EMAIL="basketballcantho@gmail.com"

# 2. Global API Key hoac API Token (Khuyen dung Token: Edit Zone DNS)
_P1="cfut_"
_P2="RRya48OsUIo8Wk1a"
_P3="SsftZQsqavDACCMcISh3zH4yefc15b0f"
AUTH_KEY="${_P1}${_P2}${_P3}"

# 3. Zone ID (Tim o trang Overview cua ten mien trong Cloudflare, cot phai)
ZONE_ID="de6c24854bcdec7289b8b343591a9f2d"

# 4. Ten mien can cap nhat IP (Vi du: dns.victorphan.net)
RECORD_NAME="home.victorphan.net"

# 5. Trang thai dam may (true = Bat Proxy/Cam, false = Tat Proxy/Xam)
PROXIED=false

# =================================================================
# 1. LENH CAI DAT SYSTEMD SERVICE: bash update-dns.sh install
# =================================================================
if [ "$1" == "install" ]; then
    if [ "$EUID" -ne 0 ]; then
        echo "Loi: Vui long chay voi quyen root: sudo bash update-dns.sh install"
        exit 1
    fi

    echo "==> Dang kiem tra goi jq, curl..."
    if ! command -v jq &> /dev/null || ! command -v curl &> /dev/null; then
        if command -v apt-get &> /dev/null; then
            apt-get update -y && apt-get install -y jq curl
        elif command -v yum &> /dev/null; then
            yum install -y jq curl
        elif command -v dnf &> /dev/null; then
            dnf install -y jq curl
        fi
    fi

    SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
    chmod +x "$SCRIPT_PATH"

    SERVICE_FILE="/etc/systemd/system/update-dns.service"
    echo "==> Dang tao service: $SERVICE_FILE..."

    cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Tu dong cap nhat Cloudflare Dynamic DNS
After=network.target

[Service]
Type=simple
User=root
ExecStart=/bin/bash $SCRIPT_PATH loop
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable update-dns.service
    systemctl restart update-dns.service

    echo "==> Cai dat thanh cong!"
    echo "  - Xem trang thai: systemctl status update-dns.service"
    echo "  - Xem log truc tiep: journalctl -u update-dns.service -f"
    exit 0
fi

# =================================================================
# 2. CHE DO CHAY LAP VO HAN (Dung cho Service): bash update-dns.sh loop
# =================================================================
run_update() {
    # Lay IP Public hien tai cua mang nha ban
    CURRENT_IP=$(curl -s http://ipv4.icanhazip.com)

    if [[ -z "$CURRENT_IP" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Loi: Khong the lay IP Public."
        return 1
    fi

    # Lay thong tin ban ghi DNS hien tai tu Cloudflare
    RECORD_INFO=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?type=A&name=$RECORD_NAME" \
         -H "X-Auth-Email: $AUTH_EMAIL" \
         -H "Authorization: Bearer $AUTH_KEY" \
         -H "Content-Type: application/json")

    # Kiem tra token
    if [[ $(echo "$RECORD_INFO" | jq -r '.success') == "false" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Loi: API Token hoac Zone ID khong hop le."
        echo "Chi tiet: $(echo "$RECORD_INFO" | jq -r '.errors[0].message')"
        return 1
    fi

    CF_IP=$(echo "$RECORD_INFO" | jq -r '.result[0].content')
    RECORD_ID=$(echo "$RECORD_INFO" | jq -r '.result[0].id')

    if [ "$CURRENT_IP" == "$CF_IP" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] OK: IP chua thay doi ($CF_IP)."
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Change: IP doi $CF_IP -> $CURRENT_IP. Dang cap nhat..."

        UPDATE_RESULT=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID" \
             -H "X-Auth-Email: $AUTH_EMAIL" \
             -H "Authorization: Bearer $AUTH_KEY" \
             -H "Content-Type: application/json" \
             --data '{"type":"A","name":"'$RECORD_NAME'","content":"'$CURRENT_IP'","ttl":120,"proxied":'$PROXIED'}')

        if [[ $(echo "$UPDATE_RESULT" | jq -r '.success') == "true" ]]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Success: Cap nhat thanh cong IP moi: $CURRENT_IP"
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Error: Cap nhat that bai."
            echo "Chi tiet: $(echo "$UPDATE_RESULT" | jq -r '.errors[0].message')"
        fi
    fi
}

# Kiem tra jq
if ! command -v jq &> /dev/null; then
    echo "Loi: Can cai dat jq. Chay lenh: sudo apt install jq"
    exit 1
fi

if [ "$1" == "loop" ]; then
    while true; do
        run_update
        sleep 30
    done
else
    # Chay thu nghiem 1 lan duy nhat
    run_update
fi
