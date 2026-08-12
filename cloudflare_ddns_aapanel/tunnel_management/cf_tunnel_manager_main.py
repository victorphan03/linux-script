import os, sys, json, requests

# Load aaPanel core system libraries
sys.path.append('/www/server/panel/class')
import public

class cf_tunnel_manager_main:
    def __init__(self):
        self.__plugin_path = '/www/server/panel/plugin/cf_tunnel_manager'
        self.__config_file = os.path.join(self.__plugin_path, 'config.json')

    def _get_config(self):
        if not os.path.exists(self.__config_file):
            return {}
        try:
            return json.loads(public.readFile(self.__config_file))
        except:
            return {}

    def save_config(self, get):
        api_token = getattr(get, 'api_token', '').strip()
        account_id = getattr(get, 'account_id', '').strip()
        tunnel_id = getattr(get, 'tunnel_id', '').strip()
        zone_id = getattr(get, 'zone_id', '').strip()

        if not api_token or not account_id or not tunnel_id:
            return public.returnMsg(False, 'API Token, Account ID, and Tunnel ID are required!')

        config = {
            'api_token': api_token,
            'account_id': account_id,
            'tunnel_id': tunnel_id,
            'zone_id': zone_id
        }
        public.writeFile(self.__config_file, json.dumps(config))
        return public.returnMsg(True, 'Configuration saved successfully!')

    def get_config(self, get):
        return public.returnMsg(True, self._get_config())

    def _get_tunnel_config(self, conf):
        headers = {
            "Authorization": f"Bearer {conf['api_token']}",
            "Content-Type": "application/json"
        }
        account_id = conf['account_id']
        tunnel_id = conf['tunnel_id']

        urls = [
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations",
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/tunnels/{tunnel_id}/configurations"
        ]

        last_error = "Failed to fetch tunnel configuration"
        for url in urls:
            try:
                res = requests.get(url, headers=headers, timeout=10)
                if not res.text or not res.text.strip():
                    continue
                data = res.json()
                if data.get('success'):
                    return True, data, url
                elif data.get('errors') and len(data['errors']) > 0:
                    last_error = data['errors'][0].get('message', last_error)
            except Exception as e:
                last_error = str(e)

        return False, last_error, urls[0]

    def get_routes(self, get):
        conf = self._get_config()
        if not conf.get('api_token') or not conf.get('account_id') or not conf.get('tunnel_id'):
            return public.returnMsg(False, 'API Credentials not fully configured!')

        success, data_or_err, _ = self._get_tunnel_config(conf)
        if not success:
            return public.returnMsg(False, f"Cloudflare API: {data_or_err}")

        ingress = data_or_err.get('result', {}).get('config', {}).get('ingress', []) if isinstance(data_or_err, dict) else []
        routes = [item for item in ingress if isinstance(item, dict) and 'hostname' in item]
        return public.returnMsg(True, routes)

    def add_route(self, get):
        conf = self._get_config()
        if not conf.get('api_token') or not conf.get('account_id') or not conf.get('tunnel_id'):
            return public.returnMsg(False, 'API Credentials not fully configured!')

        hostname = getattr(get, 'hostname', '').strip()
        service_target = getattr(get, 'service_target', '').strip()
        path = getattr(get, 'path', '').strip()

        if not hostname or not service_target:
            return public.returnMsg(False, 'Hostname and Service Target cannot be empty!')

        headers = {
            "Authorization": f"Bearer {conf['api_token']}",
            "Content-Type": "application/json"
        }

        # 1. Fetch current Ingress Config
        success, data_or_err, target_url = self._get_tunnel_config(conf)
        
        ingress = []
        if success and isinstance(data_or_err, dict):
            ingress = data_or_err.get('result', {}).get('config', {}).get('ingress', [])

        if not isinstance(ingress, list):
            ingress = []

        # 2. Create new Rule
        new_rule = {"hostname": hostname, "service": service_target}
        if path:
            new_rule["path"] = path

        # Ensure catch-all rule exists or insert before it
        if len(ingress) > 0 and ingress[-1].get('service') == 'http_status:404':
            ingress.insert(len(ingress) - 1, new_rule)
        else:
            ingress.append(new_rule)
            ingress.append({"service": "http_status:404"})

        # 3. Update Tunnel Config via PUT
        payload = {"config": {"ingress": ingress}}
        try:
            put_res = requests.put(target_url, headers=headers, json=payload, timeout=10)
            if not put_res.text or not put_res.text.strip():
                return public.returnMsg(False, 'Update failed: Empty response from Cloudflare API')
            put_data = put_res.json()

            if not put_data.get('success'):
                return public.returnMsg(False, put_data.get('errors', [{'message': 'Update failed'}])[0]['message'])
        except Exception as e:
            return public.returnMsg(False, f"Update error: {str(e)}")

        # 4. Automatically create CNAME Record if Zone ID is specified
        if conf.get('zone_id'):
            dns_url = f"https://api.cloudflare.com/client/v4/zones/{conf['zone_id']}/dns_records"
            dns_payload = {
                "type": "CNAME",
                "name": hostname,
                "content": f"{conf['tunnel_id']}.cfargotunnel.com",
                "proxied": True,
                "ttl": 1
            }
            try:
                requests.post(dns_url, headers=headers, json=dns_payload, timeout=5)
            except:
                pass

        return public.returnMsg(True, 'Hostname added and Tunnel updated successfully!')

    def delete_route(self, get):
        conf = self._get_config()
        if not conf.get('api_token') or not conf.get('account_id') or not conf.get('tunnel_id'):
            return public.returnMsg(False, 'API Credentials not fully configured!')

        hostname = getattr(get, 'hostname', '').strip()
        path = getattr(get, 'path', '').strip()

        headers = {
            "Authorization": f"Bearer {conf['api_token']}",
            "Content-Type": "application/json"
        }

        success, data_or_err, target_url = self._get_tunnel_config(conf)
        if not success:
            return public.returnMsg(False, f"Deletion failed: {data_or_err}")

        ingress = data_or_err.get('result', {}).get('config', {}).get('ingress', []) if isinstance(data_or_err, dict) else []

        new_ingress = [item for item in ingress if not (isinstance(item, dict) and item.get('hostname') == hostname and item.get('path', '') == path)]

        payload = {"config": {"ingress": new_ingress}}
        try:
            put_res = requests.put(target_url, headers=headers, json=payload, timeout=10)
            if not put_res.text or not put_res.text.strip():
                return public.returnMsg(False, 'Deletion failed: Empty response from Cloudflare API')
            put_data = put_res.json()

            if not put_data.get('success'):
                return public.returnMsg(False, 'Deletion failed!')

            return public.returnMsg(True, 'Hostname deleted successfully!')
        except Exception as e:
            return public.returnMsg(False, f"Processing error: {str(e)}")

    def get_accounts(self, get):
        api_token = getattr(get, 'api_token', '').strip() or self._get_config().get('api_token', '')
        if not api_token:
            return public.returnMsg(False, 'API Token required!')
        
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        accounts_dict = {}

        # 1. Try GET /accounts
        try:
            res = requests.get("https://api.cloudflare.com/client/v4/accounts", headers=headers, timeout=10)
            data = res.json()
            if data.get('success'):
                for acc in data.get('result', []):
                    accounts_dict[acc['id']] = acc.get('name', acc['id'])
        except:
            pass

        # 2. Try GET /memberships
        try:
            res = requests.get("https://api.cloudflare.com/client/v4/memberships", headers=headers, timeout=10)
            data = res.json()
            if data.get('success'):
                for mem in data.get('result', []):
                    acc = mem.get('account', {})
                    if acc.get('id'):
                        accounts_dict[acc['id']] = acc.get('name', acc['id'])
        except:
            pass

        # 3. Try GET /zones (extract account object from zones)
        try:
            res = requests.get("https://api.cloudflare.com/client/v4/zones", headers=headers, timeout=10)
            data = res.json()
            if data.get('success'):
                for z in data.get('result', []):
                    acc = z.get('account', {})
                    if acc.get('id'):
                        accounts_dict[acc['id']] = acc.get('name', acc['id'])
        except:
            pass

        accounts = [{"id": acc_id, "name": acc_name} for acc_id, acc_name in accounts_dict.items()]
        return public.returnMsg(True, accounts)

    def get_tunnels(self, get):
        api_token = getattr(get, 'api_token', '').strip() or self._get_config().get('api_token', '')
        account_id = getattr(get, 'account_id', '').strip() or self._get_config().get('account_id', '')
        
        if not api_token:
            return public.returnMsg(False, 'API Token required!')

        if not account_id:
            # Auto-resolve account_id from get_accounts
            acc_res = self.get_accounts(get)
            if acc_res.get('status') and acc_res.get('msg') and len(acc_res['msg']) > 0:
                account_id = acc_res['msg'][0]['id']

        if not account_id:
            return public.returnMsg(False, 'Account ID required!')

        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        tunnels_dict = {}
        last_error = ""

        # Endpoint 1: /cfd_tunnel
        try:
            url1 = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel?is_deleted=false"
            res1 = requests.get(url1, headers=headers, timeout=10)
            data1 = res1.json()
            if data1.get('success'):
                for t in data1.get('result', []):
                    tunnels_dict[t['id']] = {"name": t.get('name', t['id']), "status": t.get('status', '')}
            elif data1.get('errors'):
                last_error = data1['errors'][0].get('message', '')
        except Exception as e:
            last_error = str(e)

        # Endpoint 2: /tunnels
        try:
            url2 = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/tunnels?is_deleted=false"
            res2 = requests.get(url2, headers=headers, timeout=10)
            data2 = res2.json()
            if data2.get('success'):
                for t in data2.get('result', []):
                    tunnels_dict[t['id']] = {"name": t.get('name', t['id']), "status": t.get('status', '')}
            elif data2.get('errors') and not last_error:
                last_error = data2['errors'][0].get('message', '')
        except Exception as e:
            if not last_error:
                last_error = str(e)

        tunnels = [{"id": tid, "name": tinfo["name"], "status": tinfo["status"]} for tid, tinfo in tunnels_dict.items()]
        
        if not tunnels and last_error:
            return public.returnMsg(False, f"Cloudflare API: {last_error}")

        return public.returnMsg(True, tunnels)

    def get_zones(self, get):
        api_token = getattr(get, 'api_token', '').strip() or self._get_config().get('api_token', '')
        if not api_token:
            return public.returnMsg(False, 'API Token required!')
        
        url = "https://api.cloudflare.com/client/v4/zones"
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            data = res.json()
            if not data.get('success'):
                return public.returnMsg(False, data.get('errors', [{'message': 'Failed to fetch zones'}])[0]['message'])
            
            zones = [{"id": z["id"], "name": z["name"]} for z in data.get('result', [])]
            return public.returnMsg(True, zones)
        except Exception as e:
            return public.returnMsg(False, f"Error: {str(e)}")
