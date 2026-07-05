#!/bin/bash

# ==============================================================================
# Script: create_tunnel.sh (Quản lý Port Forwarding Reverse SSH)
# ==============================================================================

if [ "$EUID" -ne 0 ]; then
  echo "Vui lòng chạy script với quyền root (sudo)"
  exit 1
fi

ENV_FILE="/etc/default/reverse_ssh"
SERVICE_PATH="/etc/systemd/system/reverse-ssh.service"
PORT_CONF="/etc/reverse_ssh_ports.conf"

# Kiểm tra và cài đặt dependencies
if ! command -v stunnel4 &> /dev/null || ! command -v autossh &> /dev/null; then
    echo "Đang cài đặt các gói cần thiết (stunnel4, autossh)..."
    apt-get update
    apt-get install -y stunnel4 autossh
fi

# Hàm khởi tạo mặc định nếu chưa cài đặt
init_config() {
    echo "=== Lần đầu cấu hình Tunnel ==="
    read -p "Nhập IP/Domain của Máy A: " SERVER_A_IP
    read -p "Nhập port Stunnel Server (VD: 8443): " STUNNEL_PORT
    STUNNEL_PORT=${STUNNEL_PORT:-8443}
    read -p "Nhập User SSH Máy A (VD: root): " SERVER_A_USER
    
    echo "Tìm SSH Key..."
    keys=()
    
    # Tìm tất cả các khóa trong /root và /home
    search_dirs=("/root/.ssh")
    for d in /home/*/.ssh; do
        if [ -d "$d" ]; then
            search_dirs+=("$d")
        fi
    done

    for d in "${search_dirs[@]}"; do
        if [ -d "$d" ]; then
            for f in "$d/"*; do
                if [ -f "$f" ] && [[ "$f" != *.pub ]] && [[ "$f" != *known_hosts* ]] && [[ "$f" != *authorized_keys* ]] && [[ "$f" != *config* ]]; then 
                    keys+=("$f")
                fi
            done
        fi
    done
    
    keys+=("Nhập đường dẫn thủ công")

    echo "Chọn key:"
    select KEY_FILE in "${keys[@]}"; do
        if [ "$KEY_FILE" == "Nhập đường dẫn thủ công" ]; then
            read -p "Nhập đường dẫn tuyệt đối tới Private Key (VD: /home/x79/.ssh/id_rsa): " KEY_FILE
            break
        elif [ -n "$KEY_FILE" ]; then
            break
        else 
            echo "Chọn sai."
        fi
    done
    
    cat > "$ENV_FILE" <<ENDFILE
SERVER_A_USER=$SERVER_A_USER
SSH_KEY_PATH=$KEY_FILE
ENDFILE
    
    echo "Cấu hình Stunnel Client..."
    mkdir -p /etc/stunnel
    cat > /etc/stunnel/stunnel.conf <<EOF
client = yes
[ssh-reverse]
accept = 127.0.0.1:2222
connect = $SERVER_A_IP:$STUNNEL_PORT
EOF
    # Đảm bảo dịch vụ stunnel4 được bật trên Debian/Ubuntu
    if [ -f /etc/default/stunnel4 ]; then
        sed -i 's/ENABLED=0/ENABLED=1/' /etc/default/stunnel4
    else
        echo "ENABLED=1" > /etc/default/stunnel4
    fi

    # Diệt tận gốc các tiến trình stunnel cũ bị kẹt
    killall -9 stunnel4 2>/dev/null
    
    systemctl enable stunnel4.service
    systemctl restart stunnel4.service
    sleep 2
    
    echo "Đang copy key sang Máy A qua Stunnel (Port 2222)..."
    ssh-copy-id -p 2222 -i "$KEY_FILE" -o StrictHostKeyChecking=no "$SERVER_A_USER"@127.0.0.1
    
    touch "$PORT_CONF"
}

# Đọc danh sách port
list_ports() {
    echo "=== DANH SÁCH PORT HIỆN TẠI ==="
    if [ ! -f "$PORT_CONF" ] || [ ! -s "$PORT_CONF" ]; then
        echo "Chưa có port nào được cấu hình."
        return
    fi
    local i=1
    while IFS=: read -r rport lport; do
        if [ -n "$rport" ] && [ -n "$lport" ]; then
            echo "$i) Máy A (Port $rport) ---> Máy B (Port $lport)"
            ((i++))
        fi
    done < "$PORT_CONF"
}

# Áp dụng cấu hình vào systemd
apply_service() {
    if [ ! -f "$ENV_FILE" ]; then return; fi
    source "$ENV_FILE"
    PORT_ARGS=""
    while IFS=: read -r rport lport; do
        if [ -n "$rport" ] && [ -n "$lport" ]; then
            PORT_ARGS="$PORT_ARGS -R $rport:127.0.0.1:$lport"
        fi
    done < "$PORT_CONF"
    
    cat > "$SERVICE_PATH" <<ENDFILE
[Unit]
Description=AutoSSH Reverse Tunnel Service (via Stunnel)
After=network.target stunnel4.service

[Service]
EnvironmentFile=$ENV_FILE
Environment="AUTOSSH_GATETIME=0"
ExecStart=/usr/bin/autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -o "StrictHostKeyChecking=no" -p 2222 -i \${SSH_KEY_PATH} -N $PORT_ARGS \${SERVER_A_USER}@127.0.0.1
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
ENDFILE
    systemctl daemon-reload
    systemctl restart reverse-ssh.service
    echo "[V] Đã khởi động lại dịch vụ với cấu hình mới!"
}

if [ ! -f "$ENV_FILE" ]; then
    init_config
fi

while true; do
    echo ""
    echo "====================================="
    echo " QUẢN LÝ REVERSE SSH TUNNEL (MÁY B)"
    echo "====================================="
    list_ports
    echo "-------------------------------------"
    echo "1. Thêm Port mới"
    echo "2. Xóa Port"
    echo "3. Áp dụng & Khởi động lại dịch vụ"
    echo "4. Reset cấu hình gốc (Xóa IP/Máy chủ để làm lại)"
    echo "5. Kiểm tra trạng thái dịch vụ (Status)"
    echo "6. Backup / Restore cấu hình"
    echo "7. Thoát"
    read -p "Chọn chức năng [1-7]: " choice
    
    case $choice in
        1)
            read -p "Nhập Port dịch vụ nội bộ Máy B (VD: 80): " lport
            read -p "Nhập Port remote trên Máy A (VD: 8080): " rport
            if [ -n "$lport" ] && [ -n "$rport" ]; then
                echo "$rport:$lport" >> "$PORT_CONF"
                echo "Đã thêm thành công! Hãy chọn 3 để áp dụng."
            fi
            ;;
        2)
            list_ports
            read -p "Nhập số thứ tự Port muốn xóa (VD: 1): " num
            if [[ "$num" =~ ^[0-9]+$ ]]; then
                sed -i "${num}d" "$PORT_CONF"
                echo "Đã xóa thành công! Hãy chọn 3 để áp dụng."
            fi
            ;;
        3)
            apply_service
            ;;
        4)
            echo "Đang xóa toàn bộ cấu hình cũ..."
            systemctl stop reverse-ssh.service 2>/dev/null
            rm -f "$ENV_FILE" "$PORT_CONF"
            echo "Đã reset sạch sẽ!"
            init_config
            ;;
        5)
            echo "=== TRẠNG THÁI STUNNEL ==="
            systemctl status stunnel4.service --no-pager | grep -E "Active:|Process:"
            echo ""
            echo "=== TRẠNG THÁI REVERSE SSH ==="
            systemctl status reverse-ssh.service --no-pager | grep -E "Active:|Process:"
            echo ""
            echo "=== TIẾN TRÌNH ĐANG CHẠY ==="
            ps aux | grep -E 'stunnel|autossh|ssh -N' | grep -v grep
            ;;
        6)
            echo "1. Backup cấu hình hiện tại (Lưu theo thời gian)"
            echo "2. Restore cấu hình từ danh sách backup"
            read -p "Chọn [1-2]: " br_choice
            if [ "$br_choice" == "1" ]; then
                TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
                BACKUP_FILE="reverse_ssh_backup_$TIMESTAMP.tar.gz"
                tar -czf "$BACKUP_FILE" -P /etc/default/reverse_ssh /etc/reverse_ssh_ports.conf /etc/stunnel/stunnel.conf 2>/dev/null
                echo "[V] Đã backup thành công ra file $BACKUP_FILE tại thư mục hiện tại!"
            elif [ "$br_choice" == "2" ]; then
                BACKUPS=(reverse_ssh_backup_*.tar.gz)
                if [ -e "${BACKUPS[0]}" ]; then
                    echo "Các bản backup hiện có:"
                    select b_file in "${BACKUPS[@]}"; do
                        if [ -n "$b_file" ]; then
                            echo "Đang restore từ $b_file..."
                            tar -xzf "$b_file" -P 2>/dev/null
                            systemctl restart stunnel4.service 2>/dev/null
                            apply_service
                            echo "[V] Đã restore thành công từ $b_file!"
                            break
                        else
                            echo "Lựa chọn không hợp lệ."
                        fi
                    done
                else
                    echo "[X] Không tìm thấy bản backup nào (reverse_ssh_backup_*.tar.gz)"
                fi
            fi
            ;;
        7)
            echo "Thoát chương trình."
            exit 0
            ;;
        *)
            echo "Lựa chọn không hợp lệ."
            ;;
    esac
done
