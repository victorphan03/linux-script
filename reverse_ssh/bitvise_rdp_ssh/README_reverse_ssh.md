# Hướng dẫn Cấu hình Reverse RDP qua Bitvise & Stunnel (Windows <-> Linux)

Tài liệu này hướng dẫn chi tiết cách thiết lập kết nối **Reverse SSH Tunnel** để kết nối Remote Desktop (RDP) từ máy Linux vào máy Windows thông qua sự kết hợp giữa **Bitvise SSH Client** và **Stunnel**, chạy tự động trước khi đăng nhập Windows.

---

## 1. Mô hình hoạt động
```text
[Máy Windows (RDP: 3389)] 
       │ 
       ▼ (Chuyển tiếp qua Bitvise SSH Client - S2C)
[Local Stunnel Client: 127.0.0.1:2222] (Mã hóa SSL cục bộ)
       │ 
       ▼ (Internet - Cổng 8443)
[Máy Linux - Stunnel Server: 8443] (Giải mã SSL và chuyển tiếp)
       │ 
       ▼ (Kết nối cục bộ)
[Máy Linux - SSH Server: 22] ───► Mở cổng nhận [localhost:4007]
                                       │ 
                                       ▼ (Kết nối RDP qua cổng này)
                                [Remmina Client]
```

---

## 2. Các bước cấu hình chi tiết

### BƯỚC 1: Cấu hình Stunnel trên Linux (Server) và Windows (Client)

* **Trên Linux (Stunnel Server - Nhận kết nối SSL cổng 8443):**
  Mở file `/etc/stunnel/stunnel.conf` và thêm cấu hình:
  ```ini
  [ssh-server]
  accept = 8443
  connect = 127.0.0.1:22
  cert = /etc/stunnel/server.pem
  key = /etc/stunnel/server.key
  socket = l:SO_KEEPALIVE=1
  socket = r:SO_KEEPALIVE=1
  socket = a:TCP_KEEPIDLE=15
  socket = a:TCP_KEEPINTVL=10
  socket = a:TCP_KEEPCNT=6
  ```
  *(Đảm bảo đã chạy lệnh `sudo systemctl restart stunnel4` sau khi lưu).*

* **Trên Windows (Stunnel Client - Mã hóa cổng 2222 cục bộ):**
  Mở file `C:\Program Files (x86)\stunnel\config\stunnel.conf` và thêm cấu hình:
  ```ini
  [ssh-homelab]
  client = yes
  accept = 127.0.0.1:2222
  connect = home.victorphan.net:8443
  socket = l:SO_KEEPALIVE=1
  socket = r:SO_KEEPALIVE=1
  ```
  *(Đảm bảo dịch vụ `Stunnel TLS wrapper` được chạy ngầm trong Windows Services và để khởi động ở chế độ `Automatic`).*

---

### BƯỚC 2: Cấu hình Bitvise SSH Client trên Windows
Thiết lập Bitvise kết nối qua cổng Stunnel local và tạo đường hầm ngược.

1. **Tab Login (Đăng nhập):**
   * **Host:** `127.0.0.1` | **Port:** `2222` (Kết nối qua Stunnel).
   * **Username:** `x79`.
   * **Initial method:** `publickey`.
   * **Client key:** Nhấp vào *Client key manager* để import file Private Key (ví dụ: `id_rsa`) của bạn, sau đó chọn key đó tại đây.
2. **Tab S2C (Reverse SSH):**
   Thêm một dòng mới:
   * **Listen interface:** `127.0.0.1`
   * **Port:** `4007` (Cổng nhận trên Server Linux).
   * **Destination Host:** `127.0.0.1` (hoặc `localhost`).
   * **Dest. Port:** `3389` (Cổng RDP trên Windows).
3. **Tab Options:**
   * **Automatically reconnect:** Chọn `Always` (để tự động kết nối lại khi mất mạng).
   * **Open Terminal / Open Remote Desktop:** Chọn `Never`.
4. **Lưu cấu hình:** Nhấn **Save profile as** và lưu thành file **`cnud11_stunnel.tlp`** tại thư mục:
   `C:\Users\NASPC\Documents\linux-script\bitvise_rdp_ssh\`

---

### BƯỚC 3: Cấu hình tự động khởi động (Chạy trước khi đăng nhập)
Để Bitvise tự động chạy ngầm ngay khi bật máy Windows (kể cả chưa login tài khoản), ta sử dụng Task Scheduler:

1. Nhấn `Win + R`, nhập **`taskschd.msc`** và nhấn **Enter**.
2. Chọn **Create Task...** ở cột bên phải.
3. **Tab General:** Đặt tên là `Bitvise_Tunnel_Boot`, chọn `Run whether user is logged on or not` và `Run with highest privileges`.
4. **Tab Triggers:** Nhấn **New...** -> Chọn **At startup**. (Có thể cấu hình *Delay task for* là *30 seconds* để chờ Stunnel khởi động xong trước).
5. **Tab Actions:** Nhấn **New...** -> Chọn `Start a program`:
   * **Program/script:** `"C:\Program Files (x86)\Bitvise SSH Client\BvSsh.exe"`
   * **Add arguments:** 
     ```text
     -profile="C:\Users\NASPC\Documents\linux-script\bitvise_rdp_ssh\cnud11_stunnel.tlp" -loginOnStartup -hideAll
     ```
6. **Tab Conditions:** Bỏ tích chọn `Start the task only if the computer is on AC power`.
7. Nhấn **OK** và nhập mật khẩu tài khoản Windows của bạn để lưu lại.

---

## 3. Cách kết nối RDP từ máy Linux
1. Mở ứng dụng **Remmina** (hoặc client RDP bất kỳ) trên máy Linux.
2. Thiết lập kết nối:
   * **Protocol:** `RDP`
   * **Server:** **`localhost:4007`** (hoặc `127.0.0.1:4007`)
3. Nhập tài khoản và mật khẩu máy Windows của bạn để truy cập giao diện.

---

## 4. Xử lý lỗi thường gặp

### Lỗi: `Failed to add server-to-client forwarding rule on 127.0.0.1:4007: Operation was rejected`
* **Nguyên nhân:** Cổng `4007` trên máy Linux đang bị chiếm dụng bởi một phiên kết nối SSH cũ chưa ngắt.
* **Cách khắc phục:** 
  1. Tắt các tiến trình SSH chạy ngầm cũ trên **Windows** (chạy trên PowerShell Admin):
     ```powershell
     Stop-Process -Name "wscript" -Force
     Stop-Process -Name "ssh" -Force
     ```
  2. Giải phóng cổng bị kẹt trên **Linux**:
     ```bash
     sudo kill -9 $(sudo lsof -t -i:4007)
     ```
     *(Hoặc khởi động lại dịch vụ SSH trên Linux: `sudo systemctl restart ssh`)*
