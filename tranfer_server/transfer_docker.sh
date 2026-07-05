#!/bin/bash

# Script to transfer Docker folders to another server using rsync (Push & Pull supported)

usage() {
    echo "Usage: $0 [OPTIONS] <source_folder> <destination_folder>"
    echo "Push Example: $0 /opt/docker_data user@192.168.1.100:/opt/"
    echo "Pull Example: $0 user@192.168.1.100:/opt/docker_data /opt/"
    echo ""
    echo "Options:"
    echo "  -h, --help    Show this help message"
    echo "  -d, --dry-run Perform a trial run with no changes made"
    echo "  -p, --port    Specify SSH port (default is 22)"
    echo "  -s, --sudo    Use sudo for rsync on the remote server (useful for root-owned files)"
    exit 1
}

DRY_RUN=""
SSH_PORT="22"
RSYNC_PATH=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        -d|--dry-run) DRY_RUN="--dry-run"; shift ;;
        -p|--port) SSH_PORT="$2"; shift; shift ;;
        -s|--sudo) RSYNC_PATH="--rsync-path=\"sudo rsync\""; shift ;;
        *) break ;;
    esac
done

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CONFIG_FILE="$SCRIPT_DIR/.transfer_docker.conf"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

save_config() {
    local key="$1"
    local val="$2"
    touch "$CONFIG_FILE"
    grep -v "^${key}=" "$CONFIG_FILE" > "$CONFIG_FILE.tmp" 2>/dev/null || true
    mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    echo "${key}=\"${val}\"" >> "$CONFIG_FILE"
}

select_local_path() {
    echo "Danh sách các file/thư mục tại $SCRIPT_DIR:" >&2
    ITEMS=()
    for item in "$SCRIPT_DIR"/*; do
        [ -e "$item" ] || continue
        basename_item="$(basename "$item")"
        if [ "$basename_item" != "$(basename "$0")" ]; then
            ITEMS+=("$basename_item")
        fi
    done
    
    for i in "${!ITEMS[@]}"; do
        if [ -d "$SCRIPT_DIR/${ITEMS[$i]}" ]; then
            TYPE="[Thư mục]"
        else
            TYPE="[File]   "
        fi
        echo "$((i+1)). $TYPE ${ITEMS[$i]}" >&2
    done
    
    echo "" >&2
    read -p "Chọn số tương ứng (hoặc gõ đường dẫn tuyệt đối, ví dụ /opt/docker): " INPUT_PATH < /dev/tty
    
    if [[ "$INPUT_PATH" =~ ^[0-9]+$ ]] && [ "$INPUT_PATH" -ge 1 ] && [ "$INPUT_PATH" -le "${#ITEMS[@]}" ]; then
        echo "$SCRIPT_DIR/${ITEMS[$((INPUT_PATH-1))]}"
    else
        echo "$INPUT_PATH"
    fi
}

select_remote_path() {
    local R_SERVER="$1"
    echo "" >&2
    if [ -n "$LAST_BASE_DIR" ]; then
        read -p "Nhập thư mục gốc trên server $R_SERVER để liệt kê [$LAST_BASE_DIR]: " BASE_DIR < /dev/tty
        BASE_DIR=${BASE_DIR:-$LAST_BASE_DIR}
    else
        read -p "Nhập thư mục gốc trên server $R_SERVER để liệt kê (mặc định /opt): " BASE_DIR < /dev/tty
        BASE_DIR=${BASE_DIR:-/opt}
    fi
    save_config "LAST_BASE_DIR" "$BASE_DIR"
    
    echo "Đang lấy danh sách từ $R_SERVER:$BASE_DIR ..." >&2
    # ssh into remote server and list directories and files
    mapfile -t REMOTE_ITEMS < <(ssh -p "$SSH_PORT" "$R_SERVER" "ls -1 \"$BASE_DIR\" 2>/dev/null")
    
    if [ ${#REMOTE_ITEMS[@]} -eq 0 ]; then
        echo "Thư mục trống hoặc không tồn tại, hoặc không có quyền truy cập." >&2
        read -p "Vui lòng nhập đường dẫn tuyệt đối bạn muốn dùng: " INPUT_PATH < /dev/tty
        echo "$INPUT_PATH"
        return
    fi
    
    for i in "${!REMOTE_ITEMS[@]}"; do
        echo "$((i+1)). ${REMOTE_ITEMS[$i]}" >&2
    done
    
    echo "" >&2
    read -p "Chọn số tương ứng (hoặc gõ luôn 1 đường dẫn tuyệt đối khác): " INPUT_PATH < /dev/tty
    
    if [[ "$INPUT_PATH" =~ ^[0-9]+$ ]] && [ "$INPUT_PATH" -ge 1 ] && [ "$INPUT_PATH" -le "${#REMOTE_ITEMS[@]}" ]; then
        if [[ "$BASE_DIR" == */ ]]; then
            echo "${BASE_DIR}${REMOTE_ITEMS[$((INPUT_PATH-1))]}"
        else
            echo "${BASE_DIR}/${REMOTE_ITEMS[$((INPUT_PATH-1))]}"
        fi
    else
        echo "$INPUT_PATH"
    fi
}

setup_ssh_key() {
    local R_SERVER="$1"
    echo "========================================" >&2
    echo "KIỂM TRA & CÀI ĐẶT SSH KEY" >&2
    echo "========================================" >&2
    if [ ! -f ~/.ssh/id_rsa ]; then
        echo "[INFO] Không tìm thấy SSH key (~/.ssh/id_rsa) cho user hiện tại." >&2
        echo "Đang tự động tạo mới..." >&2
        mkdir -p ~/.ssh
        ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa
        echo "[OK] Đã tạo xong SSH key." >&2
    else
        echo "[OK] SSH key (~/.ssh/id_rsa) đã tồn tại." >&2
    fi

    echo "" >&2
    read -p "Bạn có muốn copy public key lên máy tính kia ($R_SERVER) để đăng nhập tự động không? (y/n): " COPY_KEY < /dev/tty
    if [[ "$COPY_KEY" =~ ^[Yy]$ ]]; then
        echo "" >&2
        echo "Danh sách các tài khoản (user) có sẵn trên máy CỤC BỘ này:" >&2
        USERS=($(awk -F: '$3 >= 1000 && $3 < 65534 || $1 == "root" {print $1}' /etc/passwd))
        for i in "${!USERS[@]}"; do
            echo "$((i+1)). ${USERS[$i]}" >&2
        done
        echo "" >&2
        read -p "Chọn số tương ứng với user có public key bạn muốn copy (ví dụ: 1): " USER_INDEX < /dev/tty
        if [[ "$USER_INDEX" -gt 0 && "$USER_INDEX" -le "${#USERS[@]}" ]]; then
            SELECTED_USER="${USERS[$((USER_INDEX-1))]}"
            USER_HOME=$(eval echo "~$SELECTED_USER")
            PUB_KEY="$USER_HOME/.ssh/id_rsa.pub"
            if [ ! -f "$PUB_KEY" ]; then
                echo "[LỖI] Không tìm thấy public key của user $SELECTED_USER tại $PUB_KEY" >&2
            else
                echo "Đang sử dụng public key từ: $PUB_KEY" >&2
                echo "========================================" >&2
                echo "HƯỚNG DẪN: Chỉ cần nhập password của máy tính kia 1 lần duy nhất ở bước này..." >&2
                echo "========================================" >&2
                if [ -r "$PUB_KEY" ]; then
                    ssh-copy-id -i "$PUB_KEY" -p "$SSH_PORT" "$R_SERVER" >&2
                else
                    echo "[INFO] Cần quyền sudo để đọc file key của user khác..." >&2
                    sudo ssh-copy-id -i "$PUB_KEY" -p "$SSH_PORT" "$R_SERVER" >&2
                fi
                echo "[OK] Đã hoàn tất bước thiết lập SSH key." >&2
            fi
        fi
    fi
}

if [ "$#" -eq 0 ]; then
    echo "========================================"
    echo "BƯỚC 0: CHỌN HƯỚNG CHUYỂN DỮ LIỆU"
    echo "========================================"
    echo "1. Đẩy dữ liệu TỪ máy này LÊN máy khác (PUSH)"
    echo "2. Kéo dữ liệu TỪ máy khác VỀ máy này (PULL)"
    if [ -n "$LAST_DIR_CHOICE" ]; then
        read -p "Chọn (1 hoặc 2) [$LAST_DIR_CHOICE]: " DIR_CHOICE < /dev/tty
        DIR_CHOICE=${DIR_CHOICE:-$LAST_DIR_CHOICE}
    else
        read -p "Chọn (1 hoặc 2): " DIR_CHOICE < /dev/tty
    fi
    save_config "LAST_DIR_CHOICE" "$DIR_CHOICE"
    
    echo ""
    if [ -n "$LAST_REMOTE_SERVER" ]; then
        read -p "Nhập user và IP của máy tính kia [$LAST_REMOTE_SERVER]: " REMOTE_SERVER < /dev/tty
        REMOTE_SERVER=${REMOTE_SERVER:-$LAST_REMOTE_SERVER}
    else
        read -p "Nhập user và IP của máy tính kia (VD: root@192.168.1.100): " REMOTE_SERVER < /dev/tty
    fi
    save_config "LAST_REMOTE_SERVER" "$REMOTE_SERVER"
    
    if [ "$DIR_CHOICE" == "1" ]; then
        DIRECTION="PUSH"
    elif [ "$DIR_CHOICE" == "2" ]; then
        DIRECTION="PULL"
    else
        echo "Lựa chọn không hợp lệ."
        exit 1
    fi
    
    echo ""
    setup_ssh_key "$REMOTE_SERVER"
    
    echo ""
    echo "========================================"
    echo "BƯỚC 2: CHỌN DỮ LIỆU"
    echo "========================================"
    
    if [ "$DIRECTION" == "PUSH" ]; then
        echo "--- CHỌN DỮ LIỆU NGUỒN (TRÊN MÁY NÀY) ---"
        SOURCE=$(select_local_path)
        echo ""
        echo "--- CHỌN ĐÍCH ĐẾN (TRÊN SERVER $REMOTE_SERVER) ---"
        DEST_PATH=$(select_remote_path "$REMOTE_SERVER")
        DEST="$REMOTE_SERVER:$DEST_PATH"
    else
        echo "--- CHỌN DỮ LIỆU NGUỒN (TỪ MÁY $REMOTE_SERVER) ---"
        SOURCE_PATH=$(select_remote_path "$REMOTE_SERVER")
        SOURCE="$REMOTE_SERVER:$SOURCE_PATH"
        echo ""
        echo "--- CHỌN THƯ MỤC LƯU TRỮ (TRÊN MÁY NÀY) ---"
        DEST=$(select_local_path)
    fi

elif [ "$#" -eq 2 ]; then
    SOURCE="$1"
    DEST="$2"
    if [[ "$DEST" == *":"* ]]; then
        REMOTE_SERVER="${DEST%:*}"
        DIRECTION="PUSH"
    elif [[ "$SOURCE" == *":"* ]]; then
        REMOTE_SERVER="${SOURCE%:*}"
        DIRECTION="PULL"
    else
        REMOTE_SERVER=""
        DIRECTION="LOCAL"
    fi
    
    if [ -n "$REMOTE_SERVER" ]; then
        setup_ssh_key "$REMOTE_SERVER"
    fi
else
    echo "Lỗi: Vui lòng truyền đủ 2 tham số (nguồn và đích) hoặc không truyền tham số nào để dùng chế độ tương tác."
    usage
fi

echo ""
echo "========================================"
echo "BƯỚC 3: BẮT ĐẦU CHUYỂN DỮ LIỆU"
echo "========================================"
echo "Hướng: $DIRECTION"
echo "Nguồn: $SOURCE"
echo "Đích: $DEST"
echo "Cổng SSH: $SSH_PORT"
if [ -n "$DRY_RUN" ]; then
    echo -e "\n[CẢNH BÁO] Đang chạy ở chế độ dry-run. Không có file nào được copy thật."
fi
if [ -n "$RSYNC_PATH" ]; then
    echo "[INFO] Đang sử dụng sudo trên server kia (-s)."
fi

echo "----------------------------------------"
COMMAND="rsync -avzP $DRY_RUN -e 'ssh -p $SSH_PORT' $RSYNC_PATH \"$SOURCE\" \"$DEST\""
echo "Thực thi lệnh: $COMMAND"
eval $COMMAND

if [ $? -eq 0 ]; then
    echo "----------------------------------------"
    echo "[THÀNH CÔNG] Dữ liệu đã được chuyển xong!"
else
    echo "----------------------------------------"
    echo "[LỖI] Quá trình chuyển thất bại. Vui lòng kiểm tra lại kết nối mạng và quyền hạn (có thể cần dùng sudo)."
    exit 1
fi
