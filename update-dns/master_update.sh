#!/bin/bash

# Vòng lặp vô tận
while true; do
    # Quét và chạy đồng loạt tất cả các file có đuôi _update-dns.sh
    for script in /root/update_dns/*_update-dns.sh; do
        bash "$script" &
    done
    
    # Đợi tất cả 8 tiến trình ngầm chạy xong 
    wait
    
    # Nghỉ 30 giây rồi quay lại từ đầu
    sleep 30
done
