#!/bin/bash

APP_DIR="/home/x79/linux-script/cf_dns_web"
APP_NAME="cf-dns-web"

check_env() {
    if ! command -v npm &> /dev/null; then
        echo "Lỗi: Chưa cài đặt Node.js và npm."
        exit 1
    fi
    if ! command -v pm2 &> /dev/null; then
        echo "[+] Đang cài đặt PM2..."
        npm install -g pm2
    fi
}

case "$1" in
    start)
        check_env
        cd "$APP_DIR" || exit 1
        echo "Khởi động $APP_NAME..."
        pm2 start npm --name "$APP_NAME" -- start
        pm2 save
        ;;
    stop)
        echo "Dừng $APP_NAME..."
        pm2 stop "$APP_NAME"
        ;;
    restart)
        echo "Khởi động lại $APP_NAME..."
        pm2 restart "$APP_NAME"
        ;;
    status)
        pm2 status "$APP_NAME"
        ;;
    logs)
        pm2 logs "$APP_NAME"
        ;;
    startup)
        check_env
        echo "Tạo cấu hình khởi động cùng hệ thống..."
        pm2 startup
        pm2 save
        ;;
    *)
        echo "Sử dụng: $0 {start|stop|restart|status|logs|startup}"
        exit 1
esac
exit 0
