#!/bin/bash

# Cloudflare Tunnel Manager aaPanel Plugin Packaging Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_ZIP="${SCRIPT_DIR}/cf_tunnel_manager.zip"

echo "=========================================="
echo " Packaging Cloudflare Tunnel Manager Plugin"
echo "=========================================="

# Check if zip utility is installed
if ! command -v zip &> /dev/null; then
    echo "Error: 'zip' command is not installed. Please install it (e.g., apt install zip / yum install zip)."
    exit 1
fi

# Navigate to script directory
cd "$SCRIPT_DIR"

# Remove existing zip if present
if [ -f "$OUTPUT_ZIP" ]; then
    rm -f "$OUTPUT_ZIP"
    echo "Removed previous package: $(basename "$OUTPUT_ZIP")"
fi

# Create clean ZIP package with essential plugin files
zip -q -r "$OUTPUT_ZIP" \
    info.json \
    cf_tunnel_manager_main.py \
    index.html \
    install.sh \
    icon.png \
    ico-cf_tunnel_manager.png \
    ico.jpg \
    Readme.md \
    -x "*.git*" "*__pycache__*" "*.DS_Store*"

if [ $? -eq 0 ]; then
    echo "Successfully created plugin package!"
    echo "File: ${OUTPUT_ZIP}"
    echo "Contents:"
    zip -sf "$OUTPUT_ZIP"
    echo "=========================================="
    echo "Ready to upload to aaPanel via Third-party Plugin / Import!"
else
    echo "Error: Failed to create ZIP package."
    exit 1
fi
