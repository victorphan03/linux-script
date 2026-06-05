#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

# Install directory
pluginPath=/www/server/panel/plugin/cf_dns

Install_cf_dns()
{
    cp -f $pluginPath/cf_dns.service /etc/systemd/system/cf_dns.service
    systemctl daemon-reload
    systemctl enable cf_dns
    systemctl start cf_dns

    echo 'Successify'
}

Uninstall_cf_dns()
{
    systemctl stop cf_dns
    systemctl disable cf_dns
    rm -f /etc/systemd/system/cf_dns.service
    systemctl daemon-reload

    # Xoá toàn bộ thư mục plugin
    rm -rf $pluginPath
}

action=$1
if [ "${1}" == 'install' ];then
    Install_cf_dns
elif  [ "${1}" == 'uninstall' ];then
    Uninstall_cf_dns
fi
