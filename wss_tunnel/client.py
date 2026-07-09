import asyncio
import websockets
import ssl
import json
import os
import sys

def load_config():
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(os.path.abspath(__file__))
        
    config_path = os.path.join(application_path, 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f).get('client', {})
    except Exception:
        pass
    return {}

async def proxy_ws_to_tcp(ws, reader, writer):
    """Bidi forwarding between WebSocket and local TCP Socket."""
    
    async def ws_to_tcp():
        try:
            async for message in ws:
                if isinstance(message, str):
                    message = message.encode('utf-8')
                writer.write(message)
                await writer.drain()
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception:
            pass
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
        except Exception:
            pass
        finally:
            writer.close()
            await ws.close()

    await asyncio.gather(ws_to_tcp(), tcp_to_ws())

async def run_client():
    config = load_config()
    SERVER_HOST = config.get('server_host', '127.0.0.1')
    SERVER_PORT = config.get('server_port', 443)
    LOCAL_TARGET_PORT = config.get('local_target_port', 3389)

    # Bypass SSL checks for Firewall evasion
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    uri = f"wss://{SERVER_HOST}:{SERVER_PORT}"

    while True:
        try:
            # Connect to Homelab over WebSockets
            async with websockets.connect(uri, ssl=ssl_context) as ws:
                
                # Wait for the first trigger byte/message from the Server
                # (This happens when someone connects to the local bind port on the homelab)
                first_message = await ws.recv()
                
                # Once triggered, open a connection to the local target port (e.g. 3389)
                reader, writer = await asyncio.open_connection('127.0.0.1', LOCAL_TARGET_PORT)
                
                # Send the initial trigger message to the local target
                if isinstance(first_message, str):
                    first_message = first_message.encode('utf-8')
                writer.write(first_message)
                await writer.drain()

                # Start the bidirectional proxy
                await proxy_ws_to_tcp(ws, reader, writer)
                
        except Exception:
            # Sleep and retry on connection failure
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        pass
