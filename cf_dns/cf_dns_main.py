import os, sys, json
import public

class cf_dns_main:
    __plugin_path = '/www/server/panel/plugin/cf_dns/'
    __config_file = __plugin_path + 'configs.json'
    __settings_file = __plugin_path + 'settings.json'

    def __init__(self):
        if not os.path.exists(self.__config_file):
            public.WriteFile(self.__config_file, '[]')
        if not os.path.exists(self.__settings_file):
            public.WriteFile(self.__settings_file, json.dumps({"interval": 30}))

    # Lay danh sach config
    def get_configs(self, args):
        configs = public.ReadFile(self.__config_file)
        if not configs:
            return []
        try:
            return json.loads(configs)
        except:
            return []

    # Luu hoac them config moi
    def save_config(self, args):
        data = getattr(args, 'data', '')
        if not data:
            if hasattr(args, 'get'):
                data = args.get('data', '')
            elif type(args) is dict and 'data' in args:
                data = args['data']

        if not data:
            return public.returnMsg(False, 'Dữ liệu trống')
        
        try:
            new_conf = json.loads(data)
        except:
            return public.returnMsg(False, 'Sai định dạng dữ liệu')

        configs = self.get_configs(None)
        domain = new_conf.get('RECORD_NAME')
        old_domain = new_conf.get('OLD_RECORD_NAME')
        
        if 'OLD_RECORD_NAME' in new_conf:
            del new_conf['OLD_RECORD_NAME']
        
        # Check ton tai
        found = False
        for i, conf in enumerate(configs):
            if old_domain and conf.get('RECORD_NAME') == old_domain:
                configs[i] = new_conf
                found = True
                break
            elif not old_domain and conf.get('RECORD_NAME') == domain:
                configs[i] = new_conf
                found = True
                break
        
        if not found:
            configs.append(new_conf)

        public.WriteFile(self.__config_file, json.dumps(configs))
        return public.returnMsg(True, 'Cập nhật cấu hình thành công')

    # Lay danh sach Record tu Cloudflare
    def fetch_records(self, args):
        auth_email = getattr(args, 'AUTH_EMAIL', '')
        auth_key = getattr(args, 'AUTH_KEY', '')
        zone_id = getattr(args, 'ZONE_ID', '')
        
        if not auth_email or not auth_key or not zone_id:
            if hasattr(args, 'get'):
                auth_email = args.get('AUTH_EMAIL', '')
                auth_key = args.get('AUTH_KEY', '')
                zone_id = args.get('ZONE_ID', '')

        if not auth_email or not auth_key or not zone_id:
            return public.returnMsg(False, 'Vui lòng nhập đầy đủ Email, API Key và Zone ID')
            
        try:
            import urllib.request
            url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A"
            req = urllib.request.Request(url, headers={
                'X-Auth-Email': auth_email,
                'Authorization': f'Bearer {auth_key}',
                'Content-Type': 'application/json'
            })
            
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                
            if not res_data.get('success'):
                err_msg = res_data.get('errors', [{'message': 'Unknown error'}])[0]['message']
                return public.returnMsg(False, f'Lỗi API: {err_msg}')
                
            records = res_data.get('result', [])
            return {'status': True, 'data': records}
        except Exception as e:
            return public.returnMsg(False, f'Lỗi kết nối: {str(e)}')

    # Xoa config
    def delete_config(self, args):
        domain = getattr(args, 'domain', '')
        if not domain:
            if hasattr(args, 'get'):
                domain = args.get('domain', '')
            elif type(args) is dict and 'domain' in args:
                domain = args['domain']

        if not domain:
            return public.returnMsg(False, 'Tên miền không hợp lệ')

        configs = self.get_configs(None)
        new_configs = [c for c in configs if c.get('RECORD_NAME') != domain]
        
        public.WriteFile(self.__config_file, json.dumps(new_configs))
            
        return public.returnMsg(True, 'Xóa cấu hình thành công')

    # Check trang thai service
    def get_service_status(self, args):
        status = os.popen('systemctl is-active cf_dns').read().strip()
        return {'status': status == 'active'}

    # Khoi dong service
    def start_service(self, args):
        os.system('systemctl start cf_dns')
        return public.returnMsg(True, 'Đã khởi động service')

    # Dung service
    def stop_service(self, args):
        os.system('systemctl stop cf_dns')
        return public.returnMsg(True, 'Đã dừng service')

    # Xem log
    def get_logs(self, args):
        log_file = '/var/log/cf_dns.log'
        if not os.path.exists(log_file):
            return ""
        return public.GetNumLines(log_file, 100)

    # Xoa log
    def clear_logs(self, args):
        os.system('echo "" > /var/log/cf_dns.log')
        return public.returnMsg(True, 'Đã xóa log')

    # Bắt buộc cập nhật
    def force_update(self, args):
        try:
            if self.__plugin_path not in sys.path:
                sys.path.append(self.__plugin_path)
            import cf_dns_service
            import importlib
            importlib.reload(cf_dns_service)
            
            configs = self.get_configs(None)
            if not configs:
                return public.returnMsg(False, 'Chưa có cấu hình nào để cập nhật')
            
            current_ip = cf_dns_service.get_current_ip()
            if not current_ip:
                return public.returnMsg(False, 'Không thể lấy IP Public hiện tại')
                
            results = cf_dns_service.check_and_update_dns(current_ip, configs, force=True)
            msg = "<br>".join(results)
            return public.returnMsg(True, msg)
        except Exception as e:
            return public.returnMsg(False, f'Lỗi: {str(e)}')

    # Cai dat thoi gian
    def get_settings(self, args):
        settings = public.ReadFile(self.__settings_file)
        try:
            return json.loads(settings)
        except:
            return {"interval": 30}

    def save_settings(self, args):
        settings = self.get_settings(None)

        # Cập nhật interval nếu có
        interval = getattr(args, 'interval', '')
        if not interval and hasattr(args, 'get'):
            interval = args.get('interval', '')
            
        if interval:
            try:
                val = int(interval)
                if val >= 10:
                    settings['interval'] = val
            except:
                pass

        # Cập nhật credentials nếu có
        cf_email = getattr(args, 'cf_email', '')
        if not cf_email and hasattr(args, 'get'):
            cf_email = args.get('cf_email', '')
        if cf_email:
            settings['cf_email'] = cf_email

        cf_key = getattr(args, 'cf_key', '')
        if not cf_key and hasattr(args, 'get'):
            cf_key = args.get('cf_key', '')
        if cf_key:
            settings['cf_key'] = cf_key

        cf_zone = getattr(args, 'cf_zone', '')
        if not cf_zone and hasattr(args, 'get'):
            cf_zone = args.get('cf_zone', '')
        if cf_zone:
            settings['cf_zone'] = cf_zone

        try:
            public.WriteFile(self.__settings_file, json.dumps(settings))
            
            # Restart service
            os.system('systemctl restart cf_dns')
            return public.returnMsg(True, 'Đã lưu cài đặt')
        except:
            return public.returnMsg(False, 'Lỗi khi lưu cài đặt')
