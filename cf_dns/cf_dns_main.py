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
        
        # Check ton tai
        found = False
        for i, conf in enumerate(configs):
            if conf.get('RECORD_NAME') == domain:
                configs[i] = new_conf
                found = True
                break
        
        if not found:
            configs.append(new_conf)

        public.WriteFile(self.__config_file, json.dumps(configs))
        return public.returnMsg(True, 'Cập nhật cấu hình thành công')

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
        interval = getattr(args, 'interval', '')
        if not interval:
            if hasattr(args, 'get'):
                interval = args.get('interval', '')
            elif type(args) is dict and 'interval' in args:
                interval = args['interval']

        try:
            val = int(interval)
            if val < 10:
                return public.returnMsg(False, 'Thời gian quét phải >= 10 giây')
            public.WriteFile(self.__settings_file, json.dumps({"interval": val}))
            
            # Restart service
            os.system('systemctl restart cf_dns')
            return public.returnMsg(True, 'Đã lưu cài đặt và khởi động lại dịch vụ')
        except:
            return public.returnMsg(False, 'Tham số không hợp lệ')
