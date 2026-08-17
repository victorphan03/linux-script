#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

# Detect script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MODULE_DIR="/usr/local/share/webmin/cf_dns"
CONFIG_DIR="/etc/webmin/cf_dns"

Install()
{
    echo 'Installing Cloudflare DNS Auto Update Webmin Module...'
    
    mkdir -p "$MODULE_DIR"
    mkdir -p "$CONFIG_DIR"

    # Copy files from script directory
    cp -rf "$SCRIPT_DIR"/* "$MODULE_DIR/"
    chmod +x "$MODULE_DIR"/*.cgi "$MODULE_DIR"/*.pl 2>/dev/null || true

    # Setup systemd service if service file exists
    if [ -f "$MODULE_DIR/cf_dns.service" ]; then
        cp -f "$MODULE_DIR/cf_dns.service" /etc/systemd/system/cf_dns.service
        systemctl daemon-reload
        systemctl enable cf_dns
        systemctl start cf_dns
    fi

    # Register module in webmin module config if webmin path exists
    if [ -f "/etc/webmin/webmin.acl" ]; then
        grep -q "cf_dns" /etc/webmin/webmin.acl || sed -i 's/$/ cf_dns/' /etc/webmin/webmin.acl
    fi

    systemctl restart webmin 2>/dev/null || true

    echo 'Successfully installed Webmin module cf_dns!'
}

Uninstall()
{
    echo 'Uninstalling Cloudflare DNS Webmin Module...'
    systemctl stop cf_dns 2>/dev/null
    systemctl disable cf_dns 2>/dev/null
    rm -f /etc/systemd/system/cf_dns.service
    systemctl daemon-reload

    rm -rf "$MODULE_DIR"
    rm -rf "$CONFIG_DIR"

    echo 'Successfully uninstalled Webmin module cf_dns!'
}

action=$1
if [ "${action}" == 'install' ]; then
    Install
elif [ "${action}" == 'uninstall' ]; then
    Uninstall
else
    Install
fi
