#!/bin/bash

# =================================================================
# CAU HINH (SUA THONG TIN CUA BAN TAI DAY)
# =================================================================

# 1. Email tai khoan Cloudflare
AUTH_EMAIL="basketballcantho@gmail.com"

# 2. Global API Key hoac API Token (Khuyen dung Token: Edit Zone DNS)
# Lay tai: https://dash.cloudflare.com/profile/api-tokens
AUTH_KEY="uaW5_3UvcEk3MPwXL5-gVK-HblaGVm-6z3ztZFiw"

# 3. Zone ID (Tim o trang Overview cua ten mien trong Cloudflare, cot phai)
ZONE_ID="de6c24854bcdec7289b8b343591a9f2d"

# 4. Ten mien can cap nhat IP (Vi du: dns.victorphan.net)
RECORD_NAME="dns.victorphan.net"

# 5. Trang thai dam may (true = Bat Proxy/Cam, false = Tat Proxy/Xam)
# Voi AdGuard Home dung NAT Port hoac VPN, hay de false
PROXIED=false

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
