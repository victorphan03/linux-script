#!/bin/bash

# =================================================================
# CAU HINH
# =================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
elif [ -f "/root/update_dns/.env" ]; then
    source "/root/update_dns/.env"
fi

# Gia tri mac dinh neu chua co trong .env
AUTH_EMAIL="${AUTH_EMAIL:-your_email@example.com}"
AUTH_KEY="${AUTH_KEY:-your_token_here}"
ZONE_ID="${ZONE_ID:-your_zone_id_here}"
RECORD_NAME="${RECORD_NAME:-home.victorphan.net}"
PROXIED="${PROXIED:-false}"

# =================================================================
# LOGIC XU LY (KHONG CAN SUA DUOI NAY)
# =================================================================

# Kiem tra xem co jq chua
if ! command -v jq &> /dev/null; then
    echo "Loi: Can cai dat jq. Chay lenh: sudo apt install jq"
    exit 1
fi

# Lay IP Public hien tai cua mang nha ban
CURRENT_IP=$(curl -s http://ipv4.icanhazip.com)

if [[ -z "$CURRENT_IP" ]]; then
    echo "Loi: Khong the lay IP Public. Kiem tra ket noi mang."
    exit 1
fi

echo "IP hien tai cua ban: $CURRENT_IP"

# Lay thong tin ban ghi DNS hien tai tu Cloudflare
RECORD_INFO=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?type=A&name=$RECORD_NAME" \
     -H "X-Auth-Email: $AUTH_EMAIL" \
     -H "Authorization: Bearer $AUTH_KEY" \
     -H "Content-Type: application/json")

# Kiem tra xem token co hop le khong
if [[ $(echo "$RECORD_INFO" | jq -r '.success') == "false" ]]; then
    echo "Loi: API Token hoac Zone ID khong hop le."
    echo "Chi tiet: $(echo "$RECORD_INFO" | jq -r '.errors[0].message')"
    exit 1
fi

# Lay IP dang luu tren Cloudflare va Record ID
CF_IP=$(echo "$RECORD_INFO" | jq -r '.result[0].content')
RECORD_ID=$(echo "$RECORD_INFO" | jq -r '.result[0].id')

echo "IP tren Cloudflare: $CF_IP"

# So sanh va cap nhat
if [ "$CURRENT_IP" == "$CF_IP" ]; then
    echo "OK: IP chua thay doi. Khong can cap nhat."
    exit 0
else
    echo "Change: IP da thay doi! Dang cap nhat len Cloudflare..."

    UPDATE_RESULT=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID" \
         -H "X-Auth-Email: $AUTH_EMAIL" \
         -H "Authorization: Bearer $AUTH_KEY" \
         -H "Content-Type: application/json" \
         --data '{"type":"A","name":"'$RECORD_NAME'","content":"'$CURRENT_IP'","ttl":120,"proxied":'$PROXIED'}')

    if [[ $(echo "$UPDATE_RESULT" | jq -r '.success') == "true" ]]; then
        echo "Success: Cap nhat thanh cong IP moi: $CURRENT_IP"
    else
        echo "Error: Cap nhat that bai."
        echo "Chi tiet: $(echo "$UPDATE_RESULT" | jq -r '.errors[0].message')"
    fi
fi
