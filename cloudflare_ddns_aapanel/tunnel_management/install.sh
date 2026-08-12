#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

pluginPath=/www/server/panel/plugin/cf_tunnel_manager

Install()
{
	echo 'Installing Cloudflare Tunnel Manager...'
	mkdir -p $pluginPath
	
	# Copy plugin icon to aaPanel static soft_ico directory
	mkdir -p /www/server/panel/BTPanel/static/img/soft_ico 2>/dev/null
	mkdir -p /www/server/panel/static/img/soft_ico 2>/dev/null
	if [ -f "$pluginPath/icon.png" ]; then
		cp -f "$pluginPath/icon.png" /www/server/panel/BTPanel/static/img/soft_ico/ico-cf_tunnel_manager.png 2>/dev/null
		cp -f "$pluginPath/icon.png" /www/server/panel/static/img/soft_ico/ico-cf_tunnel_manager.png 2>/dev/null
	fi
	echo 'Success'
}

Uninstall()
{
	echo 'Uninstalling Cloudflare Tunnel Manager...'
	rm -rf $pluginPath
	rm -f /www/server/panel/BTPanel/static/img/soft_ico/ico-cf_tunnel_manager.png 2>/dev/null
	rm -f /www/server/panel/static/img/soft_ico/ico-cf_tunnel_manager.png 2>/dev/null
	echo 'Success'
}

action=$1
if [ "${action}" == 'install' ]; then
	Install
elif [ "${action}" == 'uninstall' ]; then
	Uninstall
fi
