#!/bin/bash

# This script installs either the WSS server or client as a systemd service.

if [ "$EUID" -ne 0 ]; then
  echo "[!] Please run as root (use sudo)"
  exit 1
fi

echo "Select which WSS service you want to install:"
echo "1) WSS Client (Target Machine)"
echo "2) WSS Server (Homelab/Proxy)"
read -p "Enter choice (1 or 2): " choice

case $choice in
  1)
    SERVICE_NAME="wss-tunnel-client"
    SCRIPT_NAME="client.py"
    DESC="WSS Reverse Tunnel Client Service"
    ;;
  2)
    SERVICE_NAME="wss-tunnel-server"
    SCRIPT_NAME="server.py"
    DESC="WSS Reverse Tunnel Server Service"
    ;;
  *)
    echo "Invalid choice."
    exit 1
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_NAME"
PYTHON_EXEC=$(command -v python3)

if [ -z "$PYTHON_EXEC" ]; then
    echo "[!] python3 not found. Please install python3."
    exit 1
fi

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "[!] Cannot find $SCRIPT_PATH"
    exit 1
fi

SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

echo "[*] Creating systemd service file at $SERVICE_FILE..."

cat <<EOF > $SERVICE_FILE
[Unit]
Description=$DESC
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PYTHON_EXEC $SCRIPT_PATH
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "[*] Reloading systemd daemon..."
systemctl daemon-reload

echo "[*] Enabling service to start on boot..."
systemctl enable $SERVICE_NAME

echo "[*] Starting the service..."
systemctl start $SERVICE_NAME

echo "[+] Successfully installed and started $SERVICE_NAME."
echo "    Check status using: systemctl status $SERVICE_NAME"
