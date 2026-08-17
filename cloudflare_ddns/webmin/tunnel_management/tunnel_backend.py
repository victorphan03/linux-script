import os, sys, json, requests

CONFIG_FILE = '/etc/webmin/tunnel_management/config.json'
RESULT_FILE = '/etc/webmin/tunnel_management/result.json'

def get_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_config(params):
    api_token = params.get('api_token', '').strip()
    account_id = params.get('account_id', '').strip()
    tunnel_id = params.get('tunnel_id', '').strip()
    zone_id = params.get('zone_id', '').strip()

    if not api_token:
        return {'status': False, 'msg': 'API Token is required!'}

    config = {
        'api_token': api_token,
        'account_id': account_id,
        'tunnel_id': tunnel_id,
        'zone_id': zone_id
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    return {'status': True, 'msg': 'Configuration saved successfully!'}

def _get_tunnel_config(conf):
    headers = {
        "Authorization": f"Bearer {conf['api_token']}",
        "Content-Type": "application/json"
    }
    account_id = conf.get('account_id', '')
    tunnel_id = conf.get('tunnel_id', '')

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

def get_routes(params):
    conf = get_config()
    if not conf.get('api_token') or not conf.get('account_id') or not conf.get('tunnel_id'):
        return {'status': False, 'msg': 'API Token, Account ID, and Tunnel ID are required! Please save them in Configuration below or click "Fetch Cloudflare Options".'}

    success, data_or_err, _ = _get_tunnel_config(conf)
    if not success:
        return {'status': False, 'msg': f"Cloudflare API Error: {data_or_err}"}

    ingress = data_or_err.get('result', {}).get('config', {}).get('ingress', []) if isinstance(data_or_err, dict) else []
    routes = [item for item in ingress if isinstance(item, dict) and 'hostname' in item]
    return {'status': True, 'msg': routes}

def fetch_accounts(params):
    api_token = params.get('api_token', '').strip() or get_config().get('api_token', '')
    if not api_token:
        return {'status': False, 'msg': 'API Token required!'}

    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    accounts_dict = {}

    try:
        res = requests.get("https://api.cloudflare.com/client/v4/accounts", headers=headers, timeout=10)
        data = res.json()
        if data.get('success'):
            for acc in data.get('result', []):
                accounts_dict[acc['id']] = acc.get('name', acc['id'])
    except:
        pass

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
    return {'status': True, 'msg': accounts}

def fetch_tunnels(params):
    api_token = params.get('api_token', '').strip() or get_config().get('api_token', '')
    account_id = params.get('account_id', '').strip() or get_config().get('account_id', '')

    if not api_token:
        return {'status': False, 'msg': 'API Token required!'}

    if not account_id:
        acc_res = fetch_accounts(params)
        if acc_res.get('status') and acc_res.get('msg') and len(acc_res['msg']) > 0:
            account_id = acc_res['msg'][0]['id']

    if not account_id:
        return {'status': False, 'msg': 'Account ID required!'}

    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    tunnels_dict = {}
    last_error = ""

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
        return {'status': False, 'msg': f"Cloudflare API: {last_error}"}

    return {'status': True, 'msg': tunnels}

def fetch_zones(params):
    api_token = params.get('api_token', '').strip() or get_config().get('api_token', '')
    if not api_token:
        return {'status': False, 'msg': 'API Token required!'}

    url = "https://api.cloudflare.com/client/v4/zones"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if not data.get('success'):
            return {'status': False, 'msg': data.get('errors', [{'message': 'Failed to fetch zones'}])[0]['message']}

        zones = [{"id": z["id"], "name": z["name"]} for z in data.get('result', [])]
        return {'status': True, 'msg': zones}
    except Exception as e:
        return {'status': False, 'msg': f"Error: {str(e)}"}

def add_route(params):
    conf = get_config()
    if not conf.get('api_token') or not conf.get('account_id') or not conf.get('tunnel_id'):
        return {'status': False, 'msg': 'API Credentials not fully configured!'}

    hostname = params.get('hostname', '').strip()
    service_target = params.get('service_target', '').strip()
    path = params.get('path', '').strip()

    if not hostname or not service_target:
        return {'status': False, 'msg': 'Hostname and Service Target cannot be empty!'}

    headers = {
        "Authorization": f"Bearer {conf['api_token']}",
        "Content-Type": "application/json"
    }

    success, data_or_err, target_url = _get_tunnel_config(conf)
    ingress = []
    if success and isinstance(data_or_err, dict):
        ingress = data_or_err.get('result', {}).get('config', {}).get('ingress', [])
    if not isinstance(ingress, list):
        ingress = []

    new_rule = {"hostname": hostname, "service": service_target}
    if path:
        new_rule["path"] = path

    if len(ingress) > 0 and ingress[-1].get('service') == 'http_status:404':
        ingress.insert(len(ingress) - 1, new_rule)
    else:
        ingress.append(new_rule)
        ingress.append({"service": "http_status:404"})

    payload = {"config": {"ingress": ingress}}
    try:
        put_res = requests.put(target_url, headers=headers, json=payload, timeout=10)
        if not put_res.text or not put_res.text.strip():
            return {'status': False, 'msg': 'Update failed: Empty response from Cloudflare API'}
        put_data = put_res.json()
        if not put_data.get('success'):
            return {'status': False, 'msg': put_data.get('errors', [{'message': 'Update failed'}])[0]['message']}
    except Exception as e:
        return {'status': False, 'msg': f"Update error: {str(e)}"}

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

    return {'status': True, 'msg': 'Hostname added and Tunnel updated successfully!'}

def delete_route(params):
    conf = get_config()
    if not conf.get('api_token') or not conf.get('account_id') or not conf.get('tunnel_id'):
        return {'status': False, 'msg': 'API Credentials not fully configured!'}

    hostname = params.get('hostname', '').strip()
    path = params.get('path', '').strip()

    headers = {
        "Authorization": f"Bearer {conf['api_token']}",
        "Content-Type": "application/json"
    }

    success, data_or_err, target_url = _get_tunnel_config(conf)
    if not success:
        return {'status': False, 'msg': f"Deletion failed: {data_or_err}"}

    ingress = data_or_err.get('result', {}).get('config', {}).get('ingress', []) if isinstance(data_or_err, dict) else []
    new_ingress = [item for item in ingress if not (isinstance(item, dict) and item.get('hostname') == hostname and item.get('path', '') == path)]

    payload = {"config": {"ingress": new_ingress}}
    try:
        put_res = requests.put(target_url, headers=headers, json=payload, timeout=10)
        if not put_res.text or not put_res.text.strip():
            return {'status': False, 'msg': 'Deletion failed: Empty response from Cloudflare API'}
        put_data = put_res.json()
        if not put_data.get('success'):
            return {'status': False, 'msg': 'Deletion failed!'}
        return {'status': True, 'msg': 'Hostname deleted successfully!'}
    except Exception as e:
        return {'status': False, 'msg': f"Processing error: {str(e)}"}

def main():
    try:
        if len(sys.argv) > 1:
            raw_input = sys.argv[1]
        else:
            raw_input = sys.stdin.read()
        req = json.loads(raw_input)
        action = req.get('action')
        params = req.get('params', {})

        if action == 'save_config':
            res = save_config(params)
        elif action == 'get_routes':
            res = get_routes(params)
        elif action == 'fetch_accounts':
            res = fetch_accounts(params)
        elif action == 'fetch_tunnels':
            res = fetch_tunnels(params)
        elif action == 'fetch_zones':
            res = fetch_zones(params)
        elif action == 'add_route':
            res = add_route(params)
        elif action == 'delete_route':
            res = delete_route(params)
        else:
            res = {'status': False, 'msg': 'Unknown action'}
    except Exception as e:
        res = {'status': False, 'msg': str(e)}

    os.makedirs('/etc/webmin/tunnel_management', exist_ok=True)
    with open(RESULT_FILE, 'w') as f:
        json.dump(res, f)
    print(json.dumps(res))

if __name__ == '__main__':
    main()
