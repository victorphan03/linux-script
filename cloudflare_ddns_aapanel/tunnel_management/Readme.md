# Cloudflare Tunnel Manager for aaPanel

**Cloudflare Tunnel Manager** is a dedicated plugin for aaPanel designed to manage routing rules (**Ingress Rules / Public Hostnames**) and automatically update **DNS CNAME** records on Cloudflare via its REST API without needing to log in to the Cloudflare Zero Trust Dashboard.

---

## 🛠️ Key Features

* **Manage Ingress Rules:** View, add, or delete Hostname/Path routing rules pointing to Docker Containers (using the `global-net` Docker Network) or services running directly on the host machine (Host/Baremetal).
* **Automatic DNS CNAME Configuration:** When adding a new Hostname, the plugin automatically calls the Cloudflare API to create the corresponding CNAME record pointing to your Tunnel ID (Proxied ON).
* **Secure & Independent:** Stores API credentials locally within aaPanel's configuration directory (`config.json`) and interacts directly via aaPanel's Python environment.

---

## 📂 Project Directory Structure

The entire plugin is stored in the following directory: `/www/server/panel/plugin/cf_tunnel_manager/`

```text
cf_tunnel_manager/
├── info.json                  # Plugin metadata declaration for aaPanel
├── cf_tunnel_manager_main.py  # Core Backend handling logic & Cloudflare API calls (Python 3)
├── index.html                 # UI Dashboard interface (HTML, jQuery, Layer.js)
├── install.sh                 # aaPanel install/uninstall lifecycle script
├── build.sh                   # Packaging script for Linux (Bash)
└── build.ps1                  # Packaging script for Windows (PowerShell)
```