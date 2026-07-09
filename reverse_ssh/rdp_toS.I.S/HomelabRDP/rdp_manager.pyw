import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
import traceback
import ctypes
import threading
import subprocess
import time
import queue
import logging

def my_excepthook(t, v, tb):
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
    with open(log_path, "w", encoding="utf-8") as f:
        traceback.print_exception(t, v, tb, file=f)
sys.excepthook = my_excepthook

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None

# --- ADMIN CHECK ---
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    script = os.path.abspath(sys.argv[0])
    drive, tail = os.path.splitdrive(script)
    if drive:
        try:
            out = subprocess.check_output(
                ['powershell', '-NoProfile', '-Command', f"(Get-WmiObject Win32_LogicalDisk -Filter 'DeviceID=''{drive}''').ProviderName"],
                creationflags=0x08000000, text=True
            ).strip()
            if out:
                script = out + tail
        except Exception:
            pass
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}"', None, 1)
    sys.exit()

# --- CONFIG ---
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config_ssh.json")
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
        "SshExePath": "ssh.exe", "AutoStartTunnel": True
    }

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

# --- QUEUE LOGGER ---
log_queue = queue.Queue()
class QueueHandler(logging.Handler):
    def emit(self, record):
        log_queue.put(self.format(record))

logger = logging.getLogger("ReverseSSH")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] %(message)s', '%H:%M:%S')
qh = QueueHandler()
qh.setFormatter(formatter)
logger.addHandler(qh)

# --- APP ---
class HomelabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.root = self
        self.title("Reverse SSH Manager")
        self.geometry("600x450")
        self.resizable(False, False)
        
        style = ttk.Style(self)
        style.theme_use('clam')
        
        self.config = load_config()
        self.ssh_process = None
        self.running = True
        
        self.build_ui()
        self.process_queue()
        
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        self.root.bind('<Unmap>', self.on_unmap)
        self.icon = None
        
        if pystray is None:
            self.root.after(500, lambda: self.show_dependency_warning(is_closing=False))
        
        threading.Thread(target=self.background_worker, daemon=True).start()
        logger.info("Application started. Running as Administrator.")

    def build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.tab_dash = ttk.Frame(notebook)
        self.tab_ssh = ttk.Frame(notebook)
        
        notebook.add(self.tab_dash, text="Dashboard")
        notebook.add(self.tab_ssh, text="SSH Config")
        
        self._build_dashboard()
        self._build_ssh()

    def _build_dashboard(self):
        status_frame = ttk.LabelFrame(self.tab_dash, text="Status")
        status_frame.pack(fill='x', padx=10, pady=5)
        
        self.lbl_ssh = ttk.Label(status_frame, text="SSH Tunnel: Stopped", font=("Segoe UI", 10, "bold"), foreground="red")
        self.lbl_ssh.pack(pady=10)
        
        ctrl_frame = ttk.Frame(self.tab_dash)
        ctrl_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(ctrl_frame, text="Start Reverse SSH", command=lambda: threading.Thread(target=self.start_tunnel, daemon=True).start()).pack(side='left', padx=5)
        ttk.Button(ctrl_frame, text="Stop", command=self.stop_tunnel).pack(side='left', padx=5)
        ttk.Button(ctrl_frame, text="Exit App completely", command=self.exit_app).pack(side='right', padx=5)
        
        log_frame = ttk.LabelFrame(self.tab_dash, text="Logs")
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, state='disabled', bg="black", fg="lightgray", font=("Consolas", 9))
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)

    def _build_ssh(self):
        f = ttk.Frame(self.tab_ssh, padding=10)
        f.pack(fill='both', expand=True)
        
        def add_row(lbl, key, row):
            ttk.Label(f, text=lbl).grid(row=row, column=0, sticky='w', pady=5)
            var = tk.StringVar(value=str(self.config.get(key, "")))
            ttk.Entry(f, textvariable=var, width=30).grid(row=row, column=1, pady=5, sticky='ew')
            return var
            
        self.var_host = add_row("Host / IP:", "HomelabHost", 0)
        self.var_user = add_row("SSH User:", "SshUser", 1)
        self.var_port = add_row("SSH Port:", "SshPort", 2)
        
        ttk.Label(f, text="SSH Key Path:").grid(row=3, column=0, sticky='w', pady=5)
        self.var_key = tk.StringVar(value=self.config.get("SshKeyPath", ""))
        ttk.Entry(f, textvariable=self.var_key, width=30).grid(row=3, column=1, pady=5, sticky='ew')
        ttk.Button(f, text="Browse...", command=lambda: self.var_key.set(filedialog.askopenfilename() or self.var_key.get())).grid(row=3, column=2, padx=5)
        
        self.var_rmport = add_row("Remote RDP Port:", "RemoteRdpPort", 4)
        self.var_lcport = add_row("Local RDP Port:", "LocalRdpPort", 5)
        
        self.var_auto = tk.BooleanVar(value=self.config.get("AutoStartTunnel", True))
        ttk.Checkbutton(f, text="Auto-start tunnel on launch", variable=self.var_auto).grid(row=6, column=1, sticky='w', pady=5)

        ttk.Button(f, text="Save Config", command=self.save_ssh_config).grid(row=7, column=1, pady=10, sticky='e')
        
        lf = ttk.LabelFrame(f, text="Windows Startup")
        lf.grid(row=8, column=0, columnspan=3, pady=10, sticky='ew')
        ttk.Button(lf, text="Add to Startup (Task Scheduler)", command=self.add_to_startup).pack(side='left', padx=10, pady=10)
        ttk.Button(lf, text="Remove from Startup", command=self.remove_from_startup).pack(side='left', padx=10, pady=10)
        
        f.columnconfigure(1, weight=1)

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
        alive = self.ssh_process is not None and self.ssh_process.poll() is None
        def _update():
            self.lbl_ssh.config(text=f"SSH Tunnel: {'Running' if alive else 'Stopped'}", foreground="green" if alive else "red")
        self.after(0, _update)

    def on_unmap(self, event):
        if event.widget == self.root and self.root.state() == 'iconic':
            self.hide_window()

    def show_dependency_warning(self, is_closing=False):
        err_win = tk.Toplevel(self.root)
        err_win.title("Thiếu thư viện (Missing Dependency)")
        err_win.geometry("400x220")
        err_win.resizable(False, False)
        err_win.grab_set()
        
        ttk.Label(err_win, text="Phần mềm cần 2 thư viện 'pystray' và 'Pillow'\nđể thu nhỏ xuống góc màn hình.", justify="center").pack(pady=15)
        ttk.Label(err_win, text="Copy lệnh dưới đây và chạy trong CMD:").pack(pady=5)
        
        cmd_entry = ttk.Entry(err_win, justify="center", font=("Consolas", 10))
        cmd_entry.insert(0, "pip install pystray pillow")
        cmd_entry.config(state="readonly")
        cmd_entry.pack(fill="x", padx=40, pady=5)
        
        if is_closing:
            ttk.Label(err_win, text="Phần mềm sẽ tắt để tránh lỗi chạy ngầm.").pack(pady=10)
            ttk.Button(err_win, text="Đã hiểu (Thoát)", command=self.root.destroy).pack(pady=5)
        else:
            ttk.Label(err_win, text="Vui lòng cài đặt để dùng tính năng chạy ngầm.").pack(pady=10)
            ttk.Button(err_win, text="Đã hiểu", command=err_win.destroy).pack(pady=5)

    def hide_window(self):
        if pystray is None:
            self.show_dependency_warning(is_closing=True)
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
        self.stop_tunnel()
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
            self.icon = pystray.Icon("ReverseSSH", image, "Reverse SSH Manager", menu)
            threading.Thread(target=self.icon.run, daemon=True).start()
        except Exception as e:
            logger.error(f"Tray icon error: {e}")

    def save_ssh_config(self):
        self.config.update({
            "HomelabHost": self.var_host.get(), "SshUser": self.var_user.get(),
            "SshPort": int(self.var_port.get()), "SshKeyPath": self.var_key.get(),
            "RemoteRdpPort": int(self.var_rmport.get()), "LocalRdpPort": int(self.var_lcport.get()),
            "AutoStartTunnel": self.var_auto.get()
        })
        save_config(self.config)
        logger.info("Saved SSH configuration.")
        if self.ssh_process:
            logger.info("Config changed, auto-restarting tunnel...")
            self.stop_tunnel()
            threading.Thread(target=self.start_tunnel, daemon=True).start()

    def kill_orphaned_ssh(self):
        try:
            subprocess.run(["taskkill", "/F", "/IM", "ssh.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
        except:
            pass

    def start_tunnel(self):
        if self.ssh_process and self.ssh_process.poll() is None:
            return
            
        self.kill_orphaned_ssh()
        
        target_host = self.config["HomelabHost"]
        target_port = self.config.get("SshPort", 22)
        
        cmd = [
            self.config.get("SshExePath", "ssh.exe"), "-N",
            "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3", "-o", "StrictHostKeyChecking=accept-new"
        ]
        if self.config.get("SshKeyPath"):
            cmd.extend(["-i", self.config["SshKeyPath"]])
        
        cmd.extend(["-p", str(target_port)])
        cmd.extend(["-R", f'{self.config["RemoteRdpPort"]}:localhost:{self.config["LocalRdpPort"]}'])
        cmd.append(f'{self.config["SshUser"]}@{target_host}')
        
        try:
            logger.info(f"Starting SSH: {' '.join(cmd)}")
            self.ssh_process = subprocess.Popen(cmd, creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            logger.info(f"SSH Tunnel started (PID: {self.ssh_process.pid})")
            
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
        if self.ssh_process:
            try:
                self.ssh_process.terminate()
                self.ssh_process.wait(timeout=2)
            except:
                self.ssh_process.kill()
            self.ssh_process = None
            logger.info("SSH Tunnel stopped.")
        self.kill_orphaned_ssh()
        self.update_status()

    def add_to_startup(self):
        try:
            py_exe = sys.executable
            script_path = os.path.abspath(__file__)
            tr_arg = f'"{py_exe}" "{script_path}"'
            subprocess.run([
                "schtasks", "/create", "/tn", "ReverseSSH_Manager",
                "/tr", tr_arg, "/sc", "onlogon", "/rl", "highest", "/f"
            ], check=True, creationflags=0x08000000)
            logger.info("Added to Task Scheduler.")
            messagebox.showinfo("Success", "Added to Task Scheduler.")
        except Exception as e:
            logger.error(f"Failed to add startup: {e}")

    def remove_from_startup(self):
        try:
            subprocess.run([
                "schtasks", "/delete", "/tn", "ReverseSSH_Manager", "/f"
            ], check=True, creationflags=0x08000000)
            logger.info("Removed from Task Scheduler.")
            messagebox.showinfo("Success", "Removed from Task Scheduler.")
        except Exception as e:
            logger.error(f"Failed to remove startup: {e}")

    def background_worker(self):
        logger.info("Background thread started.")
        while self.running:
            if self.config.get("AutoStartTunnel", True):
                if not (self.ssh_process and self.ssh_process.poll() is None):
                    logger.info("Auto-restarting SSH tunnel...")
                    self.start_tunnel()
            time.sleep(5)

if __name__ == "__main__":
    app = HomelabApp()
    app.mainloop()
