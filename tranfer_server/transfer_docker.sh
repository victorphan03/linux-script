#!/bin/bash

# Script to transfer Docker folders to another server using rsync (Push & Pull supported)

# Function to display usage
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

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        -d|--dry-run) DRY_RUN="--dry-run"; shift ;;
        -p|--port) SSH_PORT="$2"; shift; shift ;;
        -s|--sudo) RSYNC_PATH="--rsync-path=\"sudo rsync\""; shift ;;
        *) break ;;
    esac
done

if [ "$#" -eq 0 ]; then
    echo "========================================"
    echo "BƯỚC 0: CHỌN HƯỚNG CHUYỂN DỮ LIỆU"
    echo "========================================"
    echo "1. Đẩy dữ liệu TỪ máy này LÊN máy khác (PUSH)"
    echo "2. Kéo dữ liệu TỪ máy khác VỀ máy này (PULL)"
    read -p "Chọn (1 hoặc 2): " DIR_CHOICE
    
    echo ""
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    
    # Helper function to select local path
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
        # The output of the read prompt will be displayed on stderr.
        # We need to read directly from /dev/tty so it takes terminal input.
        read -p "Chọn số tương ứng (hoặc gõ đường dẫn tuyệt đối, ví dụ /opt/docker): " INPUT_PATH < /dev/tty
        
        if [[ "$INPUT_PATH" =~ ^[0-9]+$ ]] && [ "$INPUT_PATH" -ge 1 ] && [ "$INPUT_PATH" -le "${#ITEMS[@]}" ]; then
            echo "$SCRIPT_DIR/${ITEMS[$((INPUT_PATH-1))]}"
        else
            echo "$INPUT_PATH"
        fi
    }
    
    if [ "$DIR_CHOICE" == "1" ]; then
        echo "--- CHỌN DỮ LIỆU NGUỒN (TRÊN MÁY NÀY) ---"
        SOURCE=$(select_local_path)
        echo ""
        read -p "Nhập máy chủ và thư mục ĐÍCH (VD: user@192.168.1.100:/opt/): " DEST
    elif [ "$DIR_CHOICE" == "2" ]; then
        echo "--- CHỌN DỮ LIỆU NGUỒN (TỪ MÁY KHÁC) ---"
        read -p "Nhập máy chủ và thư mục NGUỒN (VD: user@192.168.1.100:/opt/docker): " SOURCE
        echo ""
        echo "--- CHỌN THƯ MỤC LƯU TRỮ (TRÊN MÁY NÀY) ---"
        DEST=$(select_local_path)
    else
        echo "Lựa chọn không hợp lệ."
        exit 1
    fi

elif [ "$#" -eq 2 ]; then
    SOURCE="$1"
    DEST="$2"
else
    echo "Lỗi: Vui lòng truyền đủ 2 tham số (nguồn và đích) hoặc không truyền tham số nào để dùng chế độ tương tác."
    usage
fi

# Detect remote server for SSH key copy
if [[ "$DEST" == *":"* ]]; then
    REMOTE_SERVER="${DEST%:*}"
    DIRECTION="PUSH"
elif [[ "$SOURCE" == *":"* ]]; then
    REMOTE_SERVER="${SOURCE%:*}"
    DIRECTION="PULL"
else
    # Local to local copy
    REMOTE_SERVER=""
    DIRECTION="LOCAL"
fi

echo "========================================"
echo "BƯỚC 1: KIỂM TRA & CÀI ĐẶT SSH KEY"
echo "========================================"

if [ -n "$REMOTE_SERVER" ]; then
    # Check if current user has id_rsa
    if [ ! -f ~/.ssh/id_rsa ]; then
        echo "[INFO] Không tìm thấy SSH key (~/.ssh/id_rsa) cho user hiện tại."
        echo "Đang tự động tạo mới..."
        mkdir -p ~/.ssh
        ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa
        echo "[OK] Đã tạo xong SSH key."
    else
        echo "[OK] SSH key (~/.ssh/id_rsa) đã tồn tại."
    fi

    echo ""
    read -p "Bạn có muốn copy public key lên máy tính kia ($REMOTE_SERVER) để đăng nhập không cần mật khẩu không? (y/n): " COPY_KEY
    if [[ "$COPY_KEY" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Danh sách các tài khoản (user) có sẵn trên máy CỤC BỘ này:"
        USERS=($(awk -F: '$3 >= 1000 && $3 < 65534 || $1 == "root" {print $1}' /etc/passwd))
        
        for i in "${!USERS[@]}"; do
            echo "$((i+1)). ${USERS[$i]}"
        done
        
        echo ""
        read -p "Chọn số tương ứng với user có public key bạn muốn copy (ví dụ: 1): " USER_INDEX
        if [[ "$USER_INDEX" -gt 0 && "$USER_INDEX" -le "${#USERS[@]}" ]]; then
            SELECTED_USER="${USERS[$((USER_INDEX-1))]}"
            
            USER_HOME=$(eval echo "~$SELECTED_USER")
            PUB_KEY="$USER_HOME/.ssh/id_rsa.pub"
            
            if [ ! -f "$PUB_KEY" ]; then
                echo "[LỖI] Không tìm thấy public key của user $SELECTED_USER tại $PUB_KEY"
                echo "Bạn cần chạy script này bằng user $SELECTED_USER để nó tự tạo key, hoặc tự tạo bằng 'ssh-keygen'."
            else
                echo "Đang sử dụng public key từ: $PUB_KEY"
                echo "========================================"
                echo "HƯỚNG DẪN: Chỉ cần nhập password của máy tính kia 1 lần duy nhất ở bước này..."
                echo "========================================"
                
                if [ -r "$PUB_KEY" ]; then
                    ssh-copy-id -i "$PUB_KEY" -p "$SSH_PORT" "$REMOTE_SERVER"
                else
                    echo "[INFO] Cần quyền sudo để đọc file key của user khác..."
                    sudo ssh-copy-id -i "$PUB_KEY" -p "$SSH_PORT" "$REMOTE_SERVER"
                fi
                echo "[OK] Đã hoàn tất bước thiết lập SSH key."
            fi
        else
            echo "[BỎ QUA] Lựa chọn không hợp lệ."
        fi
    else
        echo "[BỎ QUA] Bỏ qua bước copy SSH key."
    fi
else
    echo "[INFO] Copy cục bộ (Local to Local), không cần SSH key."
fi

echo ""
echo "========================================"
echo "BƯỚC 2: BẮT ĐẦU CHUYỂN DỮ LIỆU"
echo "========================================"
if [ "$DIRECTION" == "PUSH" ]; then
    echo "Hướng: PUSH (Đẩy dữ liệu đi)"
elif [ "$DIRECTION" == "PULL" ]; then
    echo "Hướng: PULL (Kéo dữ liệu về)"
else
    echo "Hướng: LOCAL (Copy nội bộ)"
fi

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
