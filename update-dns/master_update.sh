#!/bin/bash

# Vòng lặp vô tận
while true; do
    # Quét và chạy đồng loạt tất cả các file có đuôi _update-dns.sh hoặc update-dns.sh
    for script in /root/update_dns/*update-dns*.sh; do
        if [ -f "$script" ] && [ "$script" != "/root/update_dns/master_update.sh" ]; then
            bash "$script" &
        fi
    done
    
    # Đợi tất cả các tiến trình ngầm chạy xong 
    wait
    
    # Nghỉ 30 giây rồi quay lại từ đầu
    sleep 30
done
