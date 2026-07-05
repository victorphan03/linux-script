import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
import ctypes
import threading
import subprocess
import time
import queue
import logging
try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None

import network_ops

# --- ADMIN CHECK ---
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    script = os.path.abspath(sys.argv[0])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, script, None, 1)
    sys.exit()

# --- CONFIG ---
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "HomelabHost": "home.victorphan.net", "SshPort": 22, "SshUser": "x79",
        "SshKeyPath": "", "RemoteRdpPort": 4005, "LocalRdpPort": 3389,
        "SshExePath": "ssh.exe", "LanInterface": "Ethernet", "LanMetric": 10,
        "WiFiInterface": "WiFi 2", "WiFiMetric": 500, "WiFiGateway": "10.0.0.1",
        "DnsCheckIntervalMinutes": 10, "AutoStartTunnel": True,
        "AutoConnectWiFi": False, "WiFiProfile": ""
    }

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

# --- QUEUE LOGGER ---
log_queue = queue.Queue()
class QueueHandler(logging.Handler):
    def emit(self, record):
        log_queue.put(self.format(record))

logger = logging.getLogger("HomelabRDP")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] %(message)s', '%H:%M:%S')
qh = QueueHandler()
qh.setFormatter(formatter)
logger.addHandler(qh)
network_ops.logger = logger # Inject logger

# --- APP ---
class HomelabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.root = self
        self.title("HomelabRDP Manager (Pure Python)")
        self.geometry("700x600")
        self.resizable(False, False)
        
        # Apply clean style
        style = ttk.Style(self)
        style.theme_use('clam')
        
        self.config = load_config()
        self.interfaces = network_ops.get_network_interfaces()
        
        self.ssh_process = None
        self.running = True
        self.last_ip = ""
        
        self.build_ui()
        
        # Start queue processor for safe GUI updates
        self.process_queue()
        
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        self.root.bind('<Unmap>', self.on_unmap)
        self.icon = None
        
        # Start background thread (this thread will auto-start the tunnel if configured)
        threading.Thread(target=self.background_worker, daemon=True).start()
        
        logger.info("Application started. Running as Administrator.")

    def build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.tab_dash = ttk.Frame(notebook)
        self.tab_net = ttk.Frame(notebook)
        self.tab_ssh = ttk.Frame(notebook)
        
        notebook.add(self.tab_dash, text="Dashboard")
        notebook.add(self.tab_net, text="Network Config")
        notebook.add(self.tab_ssh, text="SSH Config")
        
        self._build_dashboard()
        self._build_network()
        self._build_ssh()

    def _build_dashboard(self):
        # Status Frame
        status_frame = ttk.LabelFrame(self.tab_dash, text="Live Status")
        status_frame.pack(fill='x', padx=10, pady=5)
        
        self.lbl_ssh = ttk.Label(status_frame, text="SSH Tunnel: Checking...", font=("Segoe UI", 10, "bold"))
        self.lbl_ssh.grid(row=0, column=0, padx=10, pady=5, sticky='w')
        
        self.lbl_fw = ttk.Label(status_frame, text="Firewall Rules: Checking...")
        self.lbl_fw.grid(row=1, column=0, padx=10, pady=5, sticky='w')
        
        self.lbl_ip = ttk.Label(status_frame, text="Homelab IP: Resolving...", foreground="blue")
        self.lbl_ip.grid(row=2, column=0, padx=10, pady=5, sticky='w')
        
        # Controls Frame
        ctrl_frame = ttk.Frame(self.tab_dash)
        ctrl_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(ctrl_frame, text="Start SSH Tunnel", command=lambda: threading.Thread(target=self.start_tunnel, daemon=True).start()).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(ctrl_frame, text="Stop SSH Tunnel", command=self.stop_tunnel).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(ctrl_frame, text="Apply Network Rules", command=self.apply_network).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(ctrl_frame, text="Remove Network Rules", command=self.remove_network).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Button(ctrl_frame, text="Exit App completely", command=self.exit_app).grid(row=1, column=2, padx=5, pady=5)
        
        # Log Box
        log_frame = ttk.LabelFrame(self.tab_dash, text="Service Logs")
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, state='disabled', bg="black", fg="lightgray", font=("Consolas", 9))
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)

    def _build_network(self):
        f = ttk.Frame(self.tab_net, padding=10)
        f.pack(fill='both', expand=True)
        
        ttk.Label(f, text="LAN Interface:").grid(row=0, column=0, sticky='w', pady=5)
        self.var_lan = tk.StringVar(value=self.config.get("LanInterface"))
        ttk.Combobox(f, textvariable=self.var_lan, values=self.interfaces).grid(row=0, column=1, pady=5, sticky='ew')
        
        ttk.Label(f, text="LAN Metric:").grid(row=1, column=0, sticky='w', pady=5)
        self.var_lan_m = tk.StringVar(value=str(self.config.get("LanMetric")))
        ttk.Entry(f, textvariable=self.var_lan_m).grid(row=1, column=1, pady=5, sticky='ew')
        
        ttk.Label(f, text="WiFi Interface:").grid(row=2, column=0, sticky='w', pady=5)
        self.var_wifi = tk.StringVar(value=self.config.get("WiFiInterface"))
        ttk.Combobox(f, textvariable=self.var_wifi, values=self.interfaces).grid(row=2, column=1, pady=5, sticky='ew')
        
        ttk.Label(f, text="WiFi Metric:").grid(row=3, column=0, sticky='w', pady=5)
        self.var_wifi_m = tk.StringVar(value=str(self.config.get("WiFiMetric")))
        ttk.Entry(f, textvariable=self.var_wifi_m).grid(row=3, column=1, pady=5, sticky='ew')
        
        ttk.Label(f, text="WiFi Gateway:").grid(row=4, column=0, sticky='w', pady=5)
        self.var_gw = tk.StringVar(value=self.config.get("WiFiGateway"))
        ttk.Entry(f, textvariable=self.var_gw).grid(row=4, column=1, pady=5, sticky='ew')
        
        wifi_conn_frame = ttk.LabelFrame(f, text="Auto-Connect WiFi (4G Router)")
        wifi_conn_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky='ew')
        
        self.var_autoconn = tk.BooleanVar(value=self.config.get("AutoConnectWiFi", False))
        ttk.Checkbutton(wifi_conn_frame, text="Connect to WiFi profile before starting tunnel", variable=self.var_autoconn).grid(row=0, column=0, columnspan=3, pady=5, sticky='w', padx=5)
        
        ttk.Label(wifi_conn_frame, text="WiFi Profile:").grid(row=1, column=0, sticky='w', pady=5, padx=5)
        self.var_wifiprof = tk.StringVar(value=self.config.get("WiFiProfile", ""))
        self.cbo_wifiprof = ttk.Combobox(wifi_conn_frame, textvariable=self.var_wifiprof)
        self.cbo_wifiprof.grid(row=1, column=1, pady=5, sticky='ew', padx=5)
        
        def refresh_wifi_profiles():
            self.cbo_wifiprof['values'] = network_ops.get_wifi_profiles()
            
        ttk.Button(wifi_conn_frame, text="Refresh List", command=refresh_wifi_profiles).grid(row=1, column=2, padx=5, pady=5)
        refresh_wifi_profiles()
        wifi_conn_frame.columnconfigure(1, weight=1)
        
        ttk.Button(f, text="Save & Apply Network", command=self.save_and_apply_network).grid(row=6, column=1, pady=10, sticky='e')
        f.columnconfigure(1, weight=1)

    def _build_ssh(self):
        f = ttk.Frame(self.tab_ssh, padding=10)
        f.pack(fill='both', expand=True)
        
        def add_row(lbl, key, row):
            ttk.Label(f, text=lbl).grid(row=row, column=0, sticky='w', pady=5)
            var = tk.StringVar(value=str(self.config.get(key, "")))
            ttk.Entry(f, textvariable=var).grid(row=row, column=1, pady=5, sticky='ew')
            return var
            
        self.var_host = add_row("Host (DDNS):", "HomelabHost", 0)
        self.var_user = add_row("SSH User:", "SshUser", 1)
        self.var_port = add_row("SSH Port:", "SshPort", 2)
        
        ttk.Label(f, text="SSH Key Path:").grid(row=3, column=0, sticky='w', pady=5)
        self.var_key = tk.StringVar(value=self.config.get("SshKeyPath", ""))
        ttk.Entry(f, textvariable=self.var_key).grid(row=3, column=1, pady=5, sticky='ew')
        ttk.Button(f, text="Browse...", command=lambda: self.var_key.set(filedialog.askopenfilename() or self.var_key.get())).grid(row=3, column=2, padx=5)
        
        self.var_rmport = add_row("Remote RDP Port:", "RemoteRdpPort", 4)
        self.var_lcport = add_row("Local RDP Port:", "LocalRdpPort", 5)
        self.var_intv = add_row("DNS Check (min):", "DnsCheckIntervalMinutes", 6)
        
        self.var_auto = tk.BooleanVar(value=self.config.get("AutoStartTunnel", True))
        ttk.Checkbutton(f, text="Auto-start tunnel on launch", variable=self.var_auto).grid(row=7, column=1, pady=5, sticky='w')
        
        ttk.Button(f, text="Save Config", command=self.save_ssh_config).grid(row=8, column=1, pady=10, sticky='e')
        
        # Auto Start Shortcut
        lf = ttk.LabelFrame(f, text="Windows Startup (Run on Boot)")
        lf.grid(row=9, column=0, columnspan=3, pady=10, sticky='ew')
        ttk.Button(lf, text="Add to Startup", command=self.add_to_startup).pack(side='left', padx=10, pady=10)
        ttk.Button(lf, text="Remove from Startup", command=self.remove_from_startup).pack(side='left', padx=10, pady=10)
        
        f.columnconfigure(1, weight=1)

    # --- ACTIONS ---
    def process_queue(self):
        while not log_queue.empty():
            msg = log_queue.get_nowait()
            self.log_text.config(state='normal')
            self.log_text.insert('end', msg + '\n')
            self.log_text.see('end')
            self.log_text.config(state='disabled')
        
        self.update_status()
        self.after(500, self.process_queue)

    def update_status(self):
        # Check SSH status
        alive = self.ssh_process is not None and self.ssh_process.poll() is None
        self.lbl_ssh.config(text=f"SSH Tunnel: {'Running' if alive else 'Stopped'}", foreground="green" if alive else "red")

    def on_unmap(self, event):
        if event.widget == self.root and self.root.state() == 'iconic':
            self.hide_window()

    def hide_window(self):
        if pystray is None:
            self.root.destroy()
            return
            
        self.root.withdraw()
        if self.icon is None:
            self.show_tray_icon()

    def show_window(self, icon=None, item=None):
        if self.icon:
            self.icon.stop()
            self.icon = None
        self.root.after(0, self.root.deiconify)
        self.root.after(0, lambda: self.root.state('normal'))

    def exit_app(self, icon=None, item=None):
        if self.icon:
            self.icon.stop()
        self.running = False
        self.root.after(0, self.root.destroy)

    def show_tray_icon(self):
        try:
            image = Image.new('RGB', (64, 64), color=(30, 30, 30))
            draw = ImageDraw.Draw(image)
            draw.ellipse((16, 16, 48, 48), fill=(0, 200, 0))
            
            menu = pystray.Menu(
                pystray.MenuItem("Show Manager", self.show_window, default=True),
                pystray.MenuItem("Exit Completely", self.exit_app)
            )
            self.icon = pystray.Icon("HomelabRDP", image, "HomelabRDP Manager", menu)
            threading.Thread(target=self.icon.run, daemon=True).start()
        except Exception as e:
            logger.error(f"Tray icon error: {e}")

    def save_and_apply_network(self):
        self.config.update({
            "LanInterface": self.var_lan.get(),
            "LanMetric": int(self.var_lan_m.get()),
            "WiFiInterface": self.var_wifi.get(),
            "WiFiMetric": int(self.var_wifi_m.get()),
            "WiFiGateway": self.var_gw.get(),
            "AutoConnectWiFi": self.var_autoconn.get(),
            "WiFiProfile": self.var_wifiprof.get()
        })
        save_config(self.config)
        threading.Thread(target=self.apply_network, daemon=True).start()

    def save_ssh_config(self):
        self.config.update({
            "HomelabHost": self.var_host.get(), "SshUser": self.var_user.get(),
            "SshPort": int(self.var_port.get()), "SshKeyPath": self.var_key.get(),
            "RemoteRdpPort": int(self.var_rmport.get()), "LocalRdpPort": int(self.var_lcport.get()),
            "DnsCheckIntervalMinutes": int(self.var_intv.get()), "AutoStartTunnel": self.var_auto.get()
        })
        save_config(self.config)
        logger.info("Saved SSH configuration.")

    def apply_network(self):
        logger.info("Applying network rules...")
        network_ops.apply_interface_metrics(self.config["LanInterface"], self.config["LanMetric"], self.config["WiFiInterface"], self.config["WiFiMetric"])
        network_ops.apply_firewall_rules(self.config["WiFiInterface"])
        if self.last_ip:
            network_ops.update_static_route(self.last_ip, self.config["WiFiInterface"], self.config["WiFiGateway"])
            network_ops.block_ip_on_lan(self.last_ip, self.config["LanInterface"])
        self.lbl_fw.config(text="Firewall Rules: Active", foreground="green")

    def remove_network(self):
        logger.info("Removing network rules...")
        network_ops.remove_firewall_rules()
        network_ops.remove_static_routes()
        self.lbl_fw.config(text="Firewall Rules: Inactive", foreground="red")

    def start_tunnel(self):
        if self.ssh_process and self.ssh_process.poll() is None:
            return
            
        if self.config.get("AutoConnectWiFi") and self.config.get("WiFiProfile"):
            logger.info(f"Auto-connecting to WiFi '{self.config['WiFiProfile']}'...")
            network_ops.connect_wifi(self.config["WiFiProfile"], self.config["WiFiInterface"])
            time.sleep(3)
            
        logger.info("Applying network rules...")
        network_ops.kill_orphaned_ssh()
        
        # Explicitly bind to WiFi IP to bypass Windows routing quirk
        wifi_ip = network_ops.get_interface_ip(self.config.get("WiFiInterface", "WiFi 2"))
        
        network_ops.kill_remote_port(
            ssh_exe=self.config.get("SshExePath", "ssh.exe"),
            host=self.config["HomelabHost"],
            port=self.config["RemoteRdpPort"],
            user=self.config["SshUser"],
            key_path=self.config.get("SshKeyPath"),
            ssh_port=self.config.get("SshPort", 22),
            bind_ip=wifi_ip
        )
        
        cmd = [
            self.config.get("SshExePath", "ssh.exe"), "-N",
            "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3", "-o", "StrictHostKeyChecking=accept-new"
        ]
        if self.config.get("SshKeyPath"):
            cmd.extend(["-i", self.config["SshKeyPath"]])
        cmd.extend(["-p", str(self.config["SshPort"])])
        cmd.extend(["-R", f'{self.config["RemoteRdpPort"]}:localhost:{self.config["LocalRdpPort"]}'])
        
        if wifi_ip:
            cmd.extend(["-b", wifi_ip])
            
        cmd.append(f'{self.config["SshUser"]}@{self.config["HomelabHost"]}')
        
        try:
            self.ssh_process = subprocess.Popen(cmd, creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            logger.info(f"SSH Tunnel started (PID: {self.ssh_process.pid})")
            
            # Start a thread to read SSH stderr and log it to the UI
            def read_ssh_stderr(proc):
                while proc.poll() is None:
                    line = proc.stderr.readline()
                    if line:
                        msg = line.decode('utf-8', errors='replace').strip()
                        if msg:
                            logger.info(f"[SSH] {msg}")
                    else:
                        break
            
            threading.Thread(target=read_ssh_stderr, args=(self.ssh_process,), daemon=True).start()
            
        except Exception as e:
            logger.error(f"Failed to start SSH: {e}")
        self.update_status()

    def stop_tunnel(self):
        if self.ssh_process and self.ssh_process.poll() is None:
            self.ssh_process.terminate()
            self.ssh_process = None
            logger.info("SSH Tunnel stopped.")
        network_ops.kill_orphaned_ssh()

    def add_to_startup(self):
        try:
            py_exe = sys.executable
            script_path = os.path.abspath(__file__)
            
            tr_arg = f'"{py_exe}" "{script_path}"'
            subprocess.run([
                "schtasks", "/create", "/tn", "HomelabRDP_Manager",
                "/tr", tr_arg, "/sc", "onlogon", "/rl", "highest", "/f"
            ], check=True, creationflags=0x08000000)
            
            startup_dir = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
            old_bat = os.path.join(startup_dir, "HomelabRDP.bat")
            if os.path.exists(old_bat):
                os.remove(old_bat)
                
            desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
            shortcut = os.path.join(desktop, "HomelabRDP (No UAC).bat")
            with open(shortcut, "w") as f:
                f.write('@echo off\nschtasks /run /tn "HomelabRDP_Manager"\n')
                
            logger.info("Added to Task Scheduler (No UAC). Desktop shortcut created.")
            messagebox.showinfo("Success", "Added to Task Scheduler. Desktop shortcut created for manual launch.")
        except Exception as e:
            logger.error(f"Failed to add startup: {e}")
            messagebox.showerror("Error", f"Failed to add startup: {e}")

    def remove_from_startup(self):
        try:
            subprocess.run([
                "schtasks", "/delete", "/tn", "HomelabRDP_Manager", "/f"
            ], check=True, creationflags=0x08000000)
            
            desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
            shortcut = os.path.join(desktop, "HomelabRDP (No UAC).bat")
            if os.path.exists(shortcut):
                os.remove(shortcut)
                
            logger.info("Removed from Task Scheduler.")
            messagebox.showinfo("Success", "Removed from Task Scheduler.")
        except Exception as e:
            logger.error(f"Failed to remove startup: {e}")
            messagebox.showerror("Error", f"Failed to remove startup: {e}")

    # --- BACKGROUND THREAD ---
    def background_worker(self):
        logger.info("Background thread started.")
        self.lbl_fw.config(text="Firewall Rules: Checking...")
        if network_ops.test_firewall_rules_active():
            self.lbl_fw.config(text="Firewall Rules: Active", foreground="green")
        else:
            self.lbl_fw.config(text="Firewall Rules: Inactive", foreground="red")
            
        while self.running:
            ip = network_ops.resolve_ip(self.config["HomelabHost"])
            if ip:
                self.lbl_ip.config(text=f"Homelab IP: {ip}", foreground="blue")
                if ip != self.last_ip:
                    logger.info(f"DNS IP changed: {self.last_ip} -> {ip}")
                    self.last_ip = ip
                    network_ops.update_static_route(ip, self.config["WiFiInterface"], self.config["WiFiGateway"])
                    network_ops.block_ip_on_lan(ip, self.config["LanInterface"])
            else:
                self.lbl_ip.config(text=f"Homelab IP: Failed to resolve", foreground="red")
            
            # Keepalive check
            if self.config.get("AutoStartTunnel", True):
                if not (self.ssh_process and self.ssh_process.poll() is None):
                    logger.info("Auto-restarting SSH tunnel...")
                    self.start_tunnel()
                    
            # Sleep in small chunks for responsive shutdown
            for _ in range(self.config.get("DnsCheckIntervalMinutes", 10) * 60):
                if not self.running: break
                time.sleep(1)

if __name__ == "__main__":
    app = HomelabApp()
    app.protocol("WM_DELETE_WINDOW", lambda: (setattr(app, 'running', False), app.stop_tunnel(), app.destroy()))
    app.mainloop()
