import subprocess
import socket
import logging

logger = logging.getLogger("HomelabRDP")

def run_ps(script):
    """Run a PowerShell script and return (success_bool, output_string)"""
    try:
        # 0x08000000 = CREATE_NO_WINDOW
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            creationflags=0x08000000
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        logger.error(f"PowerShell error: {e}")
        return False, str(e)

def get_network_interfaces():
    script = "Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Up' -or $_.Status -eq 'Disconnected' } | Select-Object -ExpandProperty Name"
    success, out = run_ps(script)
    if success and out:
        return [line.strip() for line in out.splitlines() if line.strip()]
    return ["Ethernet", "WiFi", "WiFi 2"]

def get_wifi_profiles():
    # Fetch actually available WiFi networks (SSIDs in range)
    script = "netsh wlan show networks | Select-String -Pattern 'SSID \\d+ : (.*)' | ForEach-Object { $_.Matches.Groups[1].Value.Trim() } | Where-Object { $_ -ne '' } | Sort-Object -Unique"
    success, out = run_ps(script)
    if success and out:
        return [line.strip() for line in out.splitlines() if line.strip()]
    return []

def connect_wifi(profile_name, interface_name):
    script = f'netsh wlan connect name="{profile_name}" interface="{interface_name}"'
    success, out = run_ps(script)
    if success:
        logger.info(f"Commanded connection to WiFi '{profile_name}' on '{interface_name}'")
    else:
        logger.error(f"Failed to connect to WiFi: {out}")
    return success

def get_interface_ip(interface_alias):
    script = f"(Get-NetIPAddress -InterfaceAlias '{interface_alias}' -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress"
    success, out = run_ps(script)
    if success and out:
        return out.splitlines()[0].strip()
    return None

def apply_interface_metrics(lan_name, lan_metric, wifi_name, wifi_metric):
    script = f"Set-NetIPInterface -InterfaceAlias '{lan_name}' -InterfaceMetric {lan_metric} -ErrorAction Stop; Set-NetIPInterface -InterfaceAlias '{wifi_name}' -InterfaceMetric {wifi_metric} -ErrorAction Stop"
    success, out = run_ps(script)
    if success:
        logger.info(f"Applied metric {lan_metric} to '{lan_name}' and {wifi_metric} to '{wifi_name}'")
    else:
        logger.error(f"Failed to apply metrics: {out}")
    return success

def apply_firewall_rules(wifi_name):
    remove_script = "Get-NetFirewallRule -DisplayName 'HomelabRDP -*' -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue"
    run_ps(remove_script)
    
    script = f"""
    New-NetFirewallRule -DisplayName "HomelabRDP - Block Outbound TCP on {wifi_name} except SSH" -Direction Outbound -InterfaceAlias '{wifi_name}' -Action Block -Protocol TCP -RemotePort @("1-21", "23-65535") -ErrorAction Stop | Out-Null
    New-NetFirewallRule -DisplayName "HomelabRDP - Block Outbound UDP on {wifi_name}" -Direction Outbound -InterfaceAlias '{wifi_name}' -Action Block -Protocol UDP -ErrorAction Stop | Out-Null
    """
    success, out = run_ps(script)
    if success:
        logger.info(f"Applied strict firewall block on '{wifi_name}' (except SSH)")
    else:
        logger.error(f"Failed to apply firewall: {out}")
    return success

def remove_firewall_rules():
    script = "Get-NetFirewallRule -DisplayName 'HomelabRDP -*' -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue"
    run_ps(script)
    logger.info("Removed existing firewall rules")

def test_firewall_rules_active():
    script = "Get-NetFirewallRule -DisplayName 'HomelabRDP -*' -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count"
    success, out = run_ps(script)
    try:
        return int(out) > 0
    except:
        return False

def update_static_route(destination_ip, wifi_name, wifi_gateway):
    script = f"""
    Get-NetRoute -DestinationPrefix "{destination_ip}/32" -ErrorAction SilentlyContinue | Remove-NetRoute -Confirm:$false -ErrorAction SilentlyContinue
    New-NetRoute -DestinationPrefix "{destination_ip}/32" -InterfaceAlias '{wifi_name}' -NextHop '{wifi_gateway}' -RouteMetric 5 -Confirm:$false -ErrorAction Stop | Out-Null
    """
    success, out = run_ps(script)
    if success:
        logger.info(f"Routed {destination_ip} through '{wifi_name}' via {wifi_gateway}")
    else:
        logger.error(f"Route update failed: {out}")
    return success

def block_ip_on_lan(ip, lan_name):
    script = f"""
    Get-NetFirewallRule -DisplayName "HomelabRDP - Block VPS on {lan_name}" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "HomelabRDP - Block VPS on {lan_name}" -Direction Outbound -InterfaceAlias '{lan_name}' -Action Block -RemoteAddress {ip} -ErrorAction Stop | Out-Null
    """
    success, out = run_ps(script)
    if success:
        logger.info(f"Blocked {ip} on '{lan_name}' to prevent leakage")
    else:
        logger.error(f"LAN block failed: {out}")
    return success

def remove_static_routes():
    script = "Get-NetRoute -ErrorAction SilentlyContinue | Where-Object { $_.DestinationPrefix -match '^\\d+\\.\\d+\\.\\d+\\.\\d+/32$' -and $_.RouteMetric -eq 5 } | Remove-NetRoute -Confirm:$false -ErrorAction SilentlyContinue"
    run_ps(script)
    logger.info("Removed all Homelab static routes")

def resolve_ip(hostname):
    try:
        return socket.gethostbyname(hostname)
    except:
        return None

def kill_orphaned_ssh():
    # Kills any ssh.exe process that has our target host or local stunnel in its command line using wmic
    script = "Get-CimInstance Win32_Process -Filter \"Name='ssh.exe'\" | Where-Object { $_.CommandLine -match 'home.victorphan.net' -or $_.CommandLine -match '127.0.0.1' } | Invoke-CimMethod -MethodName Terminate | Out-Null"
    run_ps(script)

def kill_orphaned_stunnel():
    # Kills any stunnel.exe process that has our stunnel.conf in its command line
    script = "Get-CimInstance Win32_Process -Filter \"Name='stunnel.exe'\" | Where-Object { $_.CommandLine -match 'stunnel.conf' } | Invoke-CimMethod -MethodName Terminate | Out-Null"
    run_ps(script)

def kill_remote_port(ssh_exe, host, port, user, key_path=None, ssh_port=22, bind_ip=None):
    logger.info(f"Attempting to clear remote port {port} on {host}...")
    cmd = [ssh_exe, "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=5", "-p", str(ssh_port)]
    if key_path:
        cmd.extend(["-i", key_path])
    if bind_ip:
        cmd.extend(["-b", bind_ip])
    
    # Since the port forward listener is often tied to the orphaned sshd session,
    # and fuser/lsof might require sudo to see it, the most effective way without sudo
    # is to kill all lingering 'sshd' processes owned by the user.
    remote_cmd = f"pkill -u {user} sshd"
    cmd.extend([f"{user}@{host}", remote_cmd])
    
    try:
        result = subprocess.run(cmd, capture_output=True, creationflags=0x08000000, timeout=10, text=True)
        logger.info(f"[SSH Kill Debug] Code: {result.returncode} | Out: {result.stdout.strip()} | Err: {result.stderr.strip()}")
    except Exception as e:
        logger.error(f"Error clearing remote port: {e}")

