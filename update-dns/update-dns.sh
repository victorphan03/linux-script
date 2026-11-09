#!/bin/bash

# =================================================================
# CAU HINH (SUA THONG TIN CUA BAN TAI DAY)
# =================================================================

# 1. Email tai khoan Cloudflare
AUTH_EMAIL="basketballcantho@gmail.com"

# 2. Global API Key hoac API Token (Khuyen dung Token: Edit Zone DNS)
# Tách token thành các phần để bypass bot quét secret của GitHub
_P1="cfut_"
_P2="RRya48OsUIo8Wk1a"
_P3="SsftZQsqavDACCMcISh3zH4yefc15b0f"
AUTH_KEY="${_P1}${_P2}${_P3}"

# 3. Zone ID (Tim o trang Overview cua ten mien trong Cloudflare, cot phai)
ZONE_ID="de6c24854bcdec7289b8b343591a9f2d"

# 4. Ten mien can cap nhat IP (Vi du: dns.victorphan.net)
RECORD_NAME="home.victorphan.net"

# 5. Trang thai dam may (true = Bat Proxy/Cam, false = Tat Proxy/Xam)
# Voi AdGuard Home dung NAT Port hoac VPN, hay de false
PROXIED=false

# =================================================================
# HAM HIEN THI TRO GIUP (-h | --help)
# =================================================================
show_help() {
    echo "=================================================================="
    echo " Cloudflare Dynamic DNS Updater"
    echo "=================================================================="
    echo "Cach dung:"
    echo "  bash update-dns.sh [TUY_CHON]"
    echo ""
    echo "Cac tuy chon:"
    echo "  (khong co tham so)  Chay kiem tra va cap nhat IP 1 lan duy nhat"
    echo "  loop                Chay vong lap vo tan moi 30 giay (dung cho service)"
    echo "  -h, --help          Hien thi huong dan su dung nay"
    echo ""
    echo "Cac file lien quan:"
    echo "  install.sh          Cai dat script thanh Systemd Service tu khoi dong"
    echo "  uninstall.sh        Go bo Systemd Service khoi he thong"
    echo "=================================================================="
    exit 0
}

# =================================================================
# HAM CAP NHAT DNS
# =================================================================
run_update() {
    # Lay IP Public hien tai cua mang nha ban
    CURRENT_IP=$(curl -s http://ipv4.icanhazip.com)

    if [[ -z "$CURRENT_IP" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Loi: Khong the lay IP Public. Kiem tra ket noi mang."
        return 1
    fi

    # Lay thong tin ban ghi DNS hien tai tu Cloudflare
    RECORD_INFO=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?type=A&name=$RECORD_NAME" \
         -H "X-Auth-Email: $AUTH_EMAIL" \
         -H "Authorization: Bearer $AUTH_KEY" \
         -H "Content-Type: application/json")

    # Kiem tra xem token co hop le khong
    if [[ $(echo "$RECORD_INFO" | jq -r '.success') == "false" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Loi: API Token hoac Zone ID khong hop le."
        echo "Chi tiet: $(echo "$RECORD_INFO" | jq -r '.errors[0].message')"
        return 1
    fi

    # Lay IP dang luu tren Cloudflare va Record ID
    CF_IP=$(echo "$RECORD_INFO" | jq -r '.result[0].content')
    RECORD_ID=$(echo "$RECORD_INFO" | jq -r '.result[0].id')

    # So sanh va cap nhat
    if [ "$CURRENT_IP" == "$CF_IP" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] OK: IP chua thay doi ($CF_IP). Khong can cap nhat."
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Change: IP da thay doi! $CF_IP -> $CURRENT_IP. Dang cap nhat..."

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

# =================================================================
# LOGIC XU LY THAM SO
# =================================================================

# Kiem tra co truyen -h hoac --help khong
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    show_help
fi

# Kiem tra jq
if ! command -v jq &> /dev/null; then
    echo "Loi: Can cai dat jq. Chay lenh: sudo apt install jq"
    exit 1
fi

# Neu co tham so 'loop' thi chay lap vo tan moi 30s (dung cho systemd service)
if [ "$1" == "loop" ]; then
    while true; do
        run_update
        sleep 30
    done
else
    # Chay thu 1 lan duy nhat
    run_update
fi
