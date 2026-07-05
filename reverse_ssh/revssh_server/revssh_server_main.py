#coding: utf-8
import sys, os, re
panelPath = '/www/server/panel/'
os.chdir(panelPath)
sys.path.append("class/")
import public

class revssh_server_main:
    __stunnel_conf = '/etc/stunnel/stunnel.conf'
    
    def get_service_name(self):
        out = public.ExecShell('systemctl list-unit-files | grep stunnel4')[0]
        if 'stunnel4.service' in out:
            return 'stunnel4'
        return 'stunnel'

    # Lấy thông tin cấu hình hiện tại
    def GetConfig(self, get):
        svc = self.get_service_name()
        status_raw = public.ExecShell('export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; systemctl is-active ' + svc)[0].strip()
        ps_check = public.ExecShell('export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; pgrep -f "stunnel.conf"')[0].strip()
        status = 'Running' if (status_raw == 'active' and ps_check) else 'Stopped'
        
        # Đọc cấu hình hiện tại
        port = '8443'
        ssh_port = '22'
        if os.path.exists(self.__stunnel_conf):
            conf = public.readFile(self.__stunnel_conf)
            match = re.search(r'accept\s*=\s*(\d+)', conf)
            if match:
                port = match.group(1)
            ssh_match = re.search(r'connect\s*=\s*127\.0\.0\.1:(\d+)', conf)
            if ssh_match:
                ssh_port = ssh_match.group(1)
                
        return public.returnMsg(True, {'status': status, 'port': port, 'ssh_port': ssh_port})

    # Lưu cấu hình và khởi động lại
    def SetConfig(self, get):
        try:
            port = get.port.strip()
            ssh_port = getattr(get, 'ssh_port', '22').strip()
            if not port.isdigit() or not ssh_port.isdigit():
                return public.returnMsg(False, 'Port must be a number!')
            
            conf = public.readFile(self.__stunnel_conf)
            if not conf:
                return public.returnMsg(False, 'Config file not found!')
                
            new_conf = []
            for line in conf.split('\n'):
                if line.strip().startswith('accept'):
                    new_conf.append('accept = ' + port)
                elif line.strip().startswith('connect'):
                    new_conf.append('connect = 127.0.0.1:' + ssh_port)
                else:
                    new_conf.append(line)
            
            public.writeFile(self.__stunnel_conf, '\n'.join(new_conf))
            svc = self.get_service_name()
            public.ExecShell('systemctl restart ' + svc)
            
            # Mở port trên OS Firewall
            public.ExecShell('ufw allow ' + str(port) + '/tcp')
            public.ExecShell('firewall-cmd --permanent --zone=public --add-port=' + str(port) + '/tcp')
            public.ExecShell('firewall-cmd --reload')
            
            # Thử thêm vào database của aaPanel để hiển thị trên giao diện Security
            try:
                import firewalls
                fw = firewalls.firewalls()
                get_fw = public.dict_obj()
                get_fw.port = str(port)
                get_fw.ps = 'Stunnel Reverse SSH'
                fw.AddAcceptPort(get_fw)
            except:
                pass

            import time
            time.sleep(1)
            return public.returnMsg(True, 'Configuration saved, firewall updated and service restarted!')
        except Exception as e:
            return public.returnMsg(False, str(e))

    # Lấy Log
    def GetLogs(self, get):
        svc = self.get_service_name()
        # Lấy 50 dòng log mới nhất từ journalctl
        log_data = public.ExecShell('journalctl -u ' + svc + ' -n 50 --no-pager')[0]
        if not log_data.strip():
            log_data = "No logs available or service hasn't generated logs yet."
        return public.returnMsg(True, log_data)

    # Điều khiển service
    def ControlService(self, get):
        import time
        action = getattr(get, 'action', '')
        svc = self.get_service_name()
        
        if action == 'start':
            public.ExecShell('export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; systemctl start ' + svc)
        elif action == 'stop':
            public.ExecShell('export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; systemctl stop ' + svc)
            kill_log = public.ExecShell('export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; killall -9 stunnel4 stunnel 2>&1')[0]
        elif action == 'restart':
            public.ExecShell('export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; systemctl stop ' + svc)
            public.ExecShell('export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; killall -9 stunnel4 stunnel 2>/dev/null')
            time.sleep(1)
            public.ExecShell('export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; systemctl start ' + svc)
        else:
            return public.returnMsg(False, 'Invalid action!')
        
        time.sleep(1.5) # Wait for state to change before returning so UI updates correctly
        
        # Check if the service actually started successfully
        if action in ['start', 'restart']:
            status_raw = public.ExecShell('export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; systemctl is-active ' + svc)[0].strip()
            if status_raw != 'active':
                # Fetch recent logs to see why it failed
                logs = public.ExecShell('export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; journalctl -u ' + svc + ' -n 10 --no-pager')[0]
                return public.returnMsg(False, 'Failed to start service! Check logs below.\n\n' + logs)
                
        if action == 'stop' and kill_log.strip():
            return public.returnMsg(True, 'Service stopped. Kill log: ' + kill_log.strip())
            
        return public.returnMsg(True, 'Service ' + action + ' executed successfully!')
