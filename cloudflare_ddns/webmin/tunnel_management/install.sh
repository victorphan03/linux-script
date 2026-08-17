#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MODULE_DIR="/usr/local/share/webmin/tunnel_management"
CONFIG_DIR="/etc/webmin/tunnel_management"

Install()
{
    echo 'Installing Cloudflare Tunnel Management Webmin Module...'
    
    mkdir -p "$MODULE_DIR"
    mkdir -p "$CONFIG_DIR"

    cp -rf "$SCRIPT_DIR"/* "$MODULE_DIR/"
    chmod +x "$MODULE_DIR"/*.cgi "$MODULE_DIR"/*.pl 2>/dev/null || true

    if [ -f "/etc/webmin/webmin.acl" ]; then
        grep -q "tunnel_management" /etc/webmin/webmin.acl || sed -i 's/$/ tunnel_management/' /etc/webmin/webmin.acl
    fi

    systemctl restart webmin 2>/dev/null || true

    echo 'Successfully installed Webmin module tunnel_management!'
}

Uninstall()
{
    echo 'Uninstalling Cloudflare Tunnel Management Webmin Module...'
    rm -rf "$MODULE_DIR"
    rm -rf "$CONFIG_DIR"

    echo 'Successfully uninstalled Webmin module tunnel_management!'
}

action=$1
if [ "${action}" == 'install' ]; then
    Install
elif [ "${action}" == 'uninstall' ]; then
    Uninstall
else
    Install
fi
