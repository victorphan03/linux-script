import os
import time
import json
import urllib.request
import logging

# Configure logging
LOG_FILE = '/var/log/cf_dns.log'
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

CONFIG_FILE = '/www/server/panel/plugin/cf_dns/configs.json'
SETTINGS_FILE = '/www/server/panel/plugin/cf_dns/settings.json'

def get_interval():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                content = f.read()
                data = json.loads(content)
                return max(10, int(data.get('interval', 30)))
    except Exception as e:
        logging.error("Failed to read settings: %s", e)
    return 30

def get_current_ip():
    try:
        req = urllib.request.Request('http://ipv4.icanhazip.com')
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8').strip()
    except Exception as e:
        logging.error("Failed to get current public IP: %s", e)
        return None

def get_configs():
    if not os.path.exists(CONFIG_FILE):
        return []
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read()
            return json.loads(content) if content else []
    except Exception as e:
        logging.error("Failed to read configs: %s", e)
        return []

def check_and_update_dns(current_ip, configs, force=False):
    results = []
    for conf in configs:
        auth_email = conf.get('AUTH_EMAIL')
        auth_key = conf.get('AUTH_KEY')
        zone_id = conf.get('ZONE_ID')
        record_name = conf.get('RECORD_NAME')
        proxied = conf.get('PROXIED') == 'true'

        if not all([auth_email, auth_key, zone_id, record_name]):
            msg = f"Bỏ qua cấu hình thiếu thông tin cho {record_name}"
            logging.warning(msg)
            results.append(msg)
            continue

        try:
            # 1. Get current DNS record IP from Cloudflare
            url = "https://api.cloudflare.com/client/v4/zones/{}/dns_records?type=A&name={}".format(zone_id, record_name)
            req = urllib.request.Request(url, headers={
                'X-Auth-Email': auth_email,
                'Authorization': 'Bearer {}'.format(auth_key),
                'Content-Type': 'application/json'
            })

            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8'))

            if not res_data.get('success'):
                err_msg = res_data.get('errors', [{'message': 'Unknown error'}])[0]['message']
                msg = f"API Error for {record_name}: {err_msg}"
                logging.error(msg)
                results.append(msg)
                continue

            records = res_data.get('result', [])
            if not records:
                msg = f"Không tìm thấy DNS record nào cho {record_name}"
                logging.error(msg)
                results.append(msg)
                continue

            cf_ip = records[0].get('content')
            record_id = records[0].get('id')

            if current_ip == cf_ip and not force:
                msg = f"[{record_name}] IP chưa thay đổi ({current_ip}), không cần cập nhật."
                logging.info(msg)
                results.append(msg)
                continue

            if force:
                logging.info("[%s] Bắt buộc cập nhật IP: %s (Bỏ qua so sánh)", record_name, current_ip)
            else:
                logging.info("[%s] IP Changed! Old: %s -> New: %s. Updating...", record_name, cf_ip, current_ip)

            # 2. Update DNS record
            update_url = "https://api.cloudflare.com/client/v4/zones/{}/dns_records/{}".format(zone_id, record_id)
            update_data = json.dumps({
                "type": "A",
                "name": record_name,
                "content": current_ip,
                "ttl": 120,
                "proxied": proxied
            }).encode('utf-8')

            req_update = urllib.request.Request(update_url, data=update_data, headers={
                'X-Auth-Email': auth_email,
                'Authorization': 'Bearer {}'.format(auth_key),
                'Content-Type': 'application/json'
            }, method='PUT')

            with urllib.request.urlopen(req_update, timeout=10) as response:
                update_res = json.loads(response.read().decode('utf-8'))

            if update_res.get('success'):
                msg = f"[{record_name}] Cập nhật thành công IP: {current_ip}"
                logging.info(msg)
                results.append(msg)
            else:
                err_msg = update_res.get('errors', [{'message': 'Unknown error'}])[0]['message']
                msg = f"[{record_name}] Lỗi cập nhật IP: {err_msg}"
                logging.error(msg)
                results.append(msg)

        except Exception as e:
            msg = f"Error processing {record_name}: {e}"
            logging.error(msg)
            results.append(msg)
            
    return results

def main():
    logging.info("Cloudflare DNS Updater Service Started")
    while True:
        try:
            configs = get_configs()
            if configs:
                current_ip = get_current_ip()
                if current_ip:
                    check_and_update_dns(current_ip, configs)
        except Exception as e:
            logging.error("Unexpected error in main loop: %s", e)
        
        interval = get_interval()
        time.sleep(interval)

if __name__ == '__main__':
    main()
