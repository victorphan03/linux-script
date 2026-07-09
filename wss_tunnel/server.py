import asyncio
import websockets
import ssl
import json
import os
import sys

# Global pool of waiting websocket clients (from the company machine)
waiting_clients = asyncio.Queue()

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f).get('server', {})
    except Exception as e:
        print(f"[!] Error loading config: {e}")
        sys.exit(1)

async def proxy_ws_to_tcp(ws, reader, writer):
    """Bidi forwarding between WebSocket and local TCP Socket."""
    
    async def ws_to_tcp():
        try:
            async for message in ws:
                # message can be bytes or str, for RDP it will be bytes
                if isinstance(message, str):
                    message = message.encode('utf-8')
                writer.write(message)
                await writer.drain()
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"[!] WS->TCP Error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def tcp_to_ws():
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                await ws.send(data)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"[!] TCP->WS Error: {e}")
        finally:
            writer.close()
            await ws.close()

    await asyncio.gather(ws_to_tcp(), tcp_to_ws())

async def handle_ws_client(websocket, *args, **kwargs):
    """Handle incoming WS connection from the remote machine (Client)."""
    client_addr = websocket.remote_address
    print(f"[+] WS Client connected from {client_addr}. Adding to pool.")
    
    # We use an asyncio Event to keep the websocket open and wait for a pairing
    paired_event = asyncio.Event()
    
    # Put a tuple of (websocket, paired_event) into the queue
    await waiting_clients.put((websocket, paired_event))
    
    # Wait until this websocket is paired with a local TCP connection and finishes
    await paired_event.wait()
    print(f"[-] WS Client {client_addr} session ended.")

async def handle_local_tcp(reader, writer):
    """Handle incoming local RDP/SSH connection (e.g. you connecting via localhost)."""
    peer = writer.get_extra_info('peername')
    print(f"[+] Local connection from {peer}.")
    
    if waiting_clients.empty():
        print("[-] No WS clients available. Dropping local connection.")
        writer.close()
        await writer.wait_closed()
        return

    # Pop a waiting WS client
    ws, paired_event = await waiting_clients.get()
    print(f"[*] Paired local connection {peer} with WS client {ws.remote_address}")
    
    try:
        # Start bidirectional proxy
        await proxy_ws_to_tcp(ws, reader, writer)
    finally:
        # Notify the WS handler that this session is done
        paired_event.set()

async def main():
    config = load_config()
    LISTEN_HOST = config.get('listen_host', '0.0.0.0')
    LISTEN_PORT = config.get('listen_port', 443)
    RDP_BIND_PORT = config.get('local_bind_port', 33890)
    CERT_FILE = config.get('cert_file', 'cert.pem')
    KEY_FILE = config.get('key_file', 'key.pem')

    # 1. Bỏ qua SSL Context (NGINX sẽ lo phần này)
    ssl_context = None

    # 2. Start WebSocket Server (Lắng nghe NGINX thay vì Client)
    print(f"[*] Starting WS Server on {LISTEN_HOST}:{LISTEN_PORT}...")
    ws_server = await websockets.serve(
        handle_ws_client, LISTEN_HOST, LISTEN_PORT, ssl=ssl_context
    )

    # 3. Start Local TCP Server (Listens for your RDP/SSH Client)
    print(f"[*] Starting Local TCP Server on 127.0.0.1:{RDP_BIND_PORT}...")
    tcp_server = await asyncio.start_server(
        handle_local_tcp, '127.0.0.1', RDP_BIND_PORT
    )

    async with ws_server, tcp_server:
        await asyncio.gather(
            ws_server.wait_closed(),
            tcp_server.serve_forever()
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[-] Server stopped.")
