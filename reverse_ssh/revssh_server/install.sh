#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
install_tmp='/tmp/bt_install.pl'
pluginPath=/www/server/panel/plugin/revssh_server

Install_revssh_server()
{
    echo "Installing Stunnel4 and OpenSSL..."
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y stunnel4 openssl
    elif command -v yum &> /dev/null; then
        yum install -y epel-release && yum install -y stunnel openssl
    fi
    
    # Generate cert if not exists
    CERT_PATH="/etc/stunnel/stunnel.pem"
    if [ ! -f "$CERT_PATH" ]; then
        openssl req -new -x509 -days 3650 -nodes -out $CERT_PATH -keyout $CERT_PATH -subj "/C=VN/ST=HCM/L=HCM/O=IT/CN=stunnel.server"
        chmod 600 $CERT_PATH
    fi
    
    # Default config
    CONF_PATH="/etc/stunnel/stunnel.conf"
    if [ ! -f "$CONF_PATH" ]; then
        # Tự động dò tìm cổng SSH của hệ thống
    SSH_PORT=$(sshd -T 2>/dev/null | grep -i "^port " | awk '{print $2}' || echo "22")
    if [ -z "$SSH_PORT" ]; then
        SSH_PORT="22"
    fi

    cat > /etc/stunnel/stunnel.conf <<EOF
pid = /var/run/stunnel.pid
cert = $CERT_PATH

[ssh]
accept = 8443
connect = 127.0.0.1:$SSH_PORT
EOF
    fi
    
    if [ -f "/etc/default/stunnel4" ]; then
        sed -i 's/ENABLED=0/ENABLED=1/g' /etc/default/stunnel4
    fi
    
    systemctl enable stunnel4
    systemctl restart stunnel4
    
    # Open Firewall Port 8443
    if command -v ufw &> /dev/null; then
        ufw allow 8443/tcp
    fi
    if command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --zone=public --add-port=8443/tcp
        firewall-cmd --reload
    fi
    
    echo 'Successify'
}

Uninstall_revssh_server()
{
    systemctl stop stunnel4
    systemctl disable stunnel4
    rm -rf $pluginPath
}

action=$1
if [ "${1}" == 'install' ];then
    Install_revssh_server
else
    Uninstall_revssh_server
fi
