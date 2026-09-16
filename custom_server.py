import asyncio
import websockets
import json
import threading
import time
import subprocess
import re
import os
import sys
import customtkinter as ctk
import requests
import jwt
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend

# ---------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ---------------------------------------------------------
PORT = 8765
MASTER_EMAIL = "tntgame1203@gmail.com"
FIREBASE_DB_URL = "https://atss-a1f9e-default-rtdb.firebaseio.com"

# Google Public Keys Cache
_GOOGLE_KEYS = {}
_GOOGLE_KEYS_EXPIRES = 0

# In-memory State
_pcs = {}
_admin_connections = set()   # set of websocket objects
_client_connections = {}     # ws -> { pc_id, ... }

# GUI Log Queue
_log_queue = []
_gui_app = None

# ---------------------------------------------------------
# UTILS & AUTH
# ---------------------------------------------------------
def log(msg):
    ts = time.strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    _log_queue.append(entry)
    print(entry)
    if len(_log_queue) > 200:
        _log_queue.pop(0)

def _get_google_public_keys():
    global _GOOGLE_KEYS, _GOOGLE_KEYS_EXPIRES
    now = time.time()
    if now < _GOOGLE_KEYS_EXPIRES and _GOOGLE_KEYS:
        return _GOOGLE_KEYS
    try:
        resp = requests.get(
            "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com",
            timeout=5
        )
        cache_control = resp.headers.get('cache-control', '')
        max_age = 3600
        match = re.search(r'max-age=(\d+)', cache_control)
        if match:
            max_age = int(match.group(1))
        _GOOGLE_KEYS = resp.json()
        _GOOGLE_KEYS_EXPIRES = now + max_age
        return _GOOGLE_KEYS
    except Exception as e:
        log(f"Error fetching Google keys: {e}")
        return _GOOGLE_KEYS

def _verify_firebase_token(token):
    keys = _get_google_public_keys()
    if not keys:
        return None, "Failed to load Google public keys"
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid or kid not in keys:
            return None, "Invalid kid"
        cert_str = keys[kid]
        cert = load_pem_x509_certificate(cert_str.encode("utf-8"), default_backend())
        public_key = cert.public_key()
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience="atss-a1f9e",
            issuer="https://securetoken.google.com/atss-a1f9e"
        )
        return decoded, None
    except Exception as e:
        return None, str(e)

def _check_auth(token, expected_role="client"):
    if expected_role == "client":
        return True, {"uid": "client", "email": "client", "role": "client"}
    decoded, err = _verify_firebase_token(token)
    if not decoded:
        return False, err
    email = decoded.get("email", "")
    uid = decoded.get("user_id", decoded.get("sub", ""))
    if email.lower() == MASTER_EMAIL.lower():
        return True, {"uid": uid, "email": email, "role": "admin"}
    try:
        r = requests.get(f"{FIREBASE_DB_URL}/users/{uid}.json", timeout=3)
        val = r.json()
        if val and val.get("approved") is True:
            return True, {"uid": uid, "email": email, "role": "admin"}
    except:
        pass
    return False, "Not approved admin"

# ---------------------------------------------------------
# WEBSOCKET SERVER (websockets 16.x compatible)
# ---------------------------------------------------------
async def _broadcast_to_admins(msg_dict):
    if not _admin_connections:
        return
    payload = json.dumps(msg_dict, ensure_ascii=False)
    dead = set()
    for ws in _admin_connections:
        try:
            await ws.send(payload)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _admin_connections.discard(ws)

async def _send_to_client(pc_id, msg_dict):
    payload = json.dumps(msg_dict, ensure_ascii=False)
    dead = []
    for ws, info in _client_connections.items():
        if info.get('pc_id') == pc_id:
            try:
                await ws.send(payload)
            except Exception:
                dead.append(ws)
    for ws in dead:
        _client_connections.pop(ws, None)

# websockets 16.x: handler takes ONE argument (the connection)
async def handler(ws):
    client_ip = ws.remote_address[0] if ws.remote_address else "Unknown"
    role = "unknown"
    pc_id = None
    user_info = {}

    try:
        # First message must be auth - 10 second timeout
        auth_msg_raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
        auth_msg = json.loads(auth_msg_raw)

        if auth_msg.get("type") != "auth":
            await ws.send(json.dumps({"type": "auth_result", "status": "fail", "reason": "First message must be auth"}))
            return

        token = auth_msg.get("token", "")
        role_req = auth_msg.get("role", "client")
        is_valid, info = _check_auth(token, role_req)

        if not is_valid:
            await ws.send(json.dumps({"type": "auth_result", "status": "fail", "reason": info}))
            return

        role = info['role']
        user_info = info

        if role == "client":
            pc_id = auth_msg.get("pc_id", "")
            if not pc_id:
                await ws.send(json.dumps({"type": "auth_result", "status": "fail", "reason": "Missing pc_id"}))
                return
            _client_connections[ws] = {"pc_id": pc_id}
            log(f"✅ Client Connected: {pc_id} ({client_ip})")
        else:
            _admin_connections.add(ws)
            log(f"✅ Admin Connected: {user_info.get('email')} ({client_ip})")
            # Send current state to newly connected admin
            await ws.send(json.dumps({"type": "full_state", "data": _pcs}, ensure_ascii=False))

        await ws.send(json.dumps({"type": "auth_result", "status": "success"}))

    except asyncio.TimeoutError:
        log(f"Auth Timeout ({client_ip})")
        return
    except Exception as e:
        log(f"Auth Error ({client_ip}): {e}")
        return

    # Main message loop
    try:
        async for message in ws:
            try:
                data = json.loads(message)
                msg_type = data.get("type")

                if role == "client":
                    if msg_type == "status":
                        payload = data.get("payload", {})
                        _pcs[pc_id] = payload
                        await _broadcast_to_admins({"type": "pc_update", "pc_id": pc_id, "data": payload})

                elif role == "admin":
                    if msg_type == "command":
                        target_pc = data.get("target_pc")
                        action = data.get("action")
                        cmd_payload = data.get("payload", {})
                        log(f"Command from {user_info.get('email')}: {action} -> {target_pc}")
                        cmd_msg = {"type": "command", "action": action, "payload": cmd_payload}

                        if target_pc == "__ALL__":
                            payload_str = json.dumps(cmd_msg, ensure_ascii=False)
                            dead = []
                            for c_ws in _client_connections.keys():
                                try:
                                    await c_ws.send(payload_str)
                                except Exception:
                                    dead.append(c_ws)
                            for c_ws in dead:
                                _client_connections.pop(c_ws, None)
                        else:
                            await _send_to_client(target_pc, cmd_msg)

            except Exception as e:
                log(f"Message Error ({client_ip}): {e}")

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        log(f"WS Error ({client_ip}): {e}")
    finally:
        if role == "client" and ws in _client_connections:
            del _client_connections[ws]
            log(f"❌ Client Disconnected: {pc_id}")
            if pc_id and pc_id in _pcs:
                _pcs[pc_id]['status'] = 'offline'
                await _broadcast_to_admins({"type": "pc_update", "pc_id": pc_id, "data": _pcs[pc_id]})
        elif role == "admin":
            _admin_connections.discard(ws)
            log(f"❌ Admin Disconnected: {user_info.get('email', 'Unknown')}")

async def main_ws():
    # websockets 16.x: websockets.serve takes (handler, host, port)
    async with websockets.serve(handler, "0.0.0.0", PORT):
        log(f"🚀 WebSocket Server started on port {PORT}")
        await asyncio.Future()  # run forever

def run_ws_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main_ws())
    except Exception as e:
        log(f"Server Error: {e}")

# ---------------------------------------------------------
# CLOUDFLARE TUNNEL
# ---------------------------------------------------------
_tunnel_url = ""

def run_cloudflare_tunnel():
    global _tunnel_url
    log("Starting Cloudflare Tunnel...")

    # cloudflared.exe 위치
    if getattr(sys, 'frozen', False):
        cf_path = os.path.join(sys._MEIPASS, "cloudflared.exe")
    else:
        cf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflared.exe")

    if not os.path.exists(cf_path):
        log(f"WARNING: {cf_path} not found! Tunnel won't start.")
        log("서버는 로컬 포트 8765에서만 실행됩니다.")
        return

    cmd = [cf_path, "tunnel", "--url", f"http://localhost:{PORT}"]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        for line in iter(proc.stdout.readline, ''):
            line = line.strip()
            if not line:
                continue
            # trycloudflare.com URL 탐지
            match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
            if match:
                raw_url = match.group(1)
                _tunnel_url = raw_url.replace("https://", "wss://")
                log(f"🌐 Tunnel Established: {_tunnel_url}")
                update_firebase_url(_tunnel_url)
                if _gui_app:
                    _gui_app.update_tunnel_url(_tunnel_url)
    except Exception as e:
        log(f"Tunnel Error: {e}")

def update_firebase_url(url):
    try:
        r = requests.put(
            f"{FIREBASE_DB_URL}/update_info/custom_server_url.json",
            json=url,
            timeout=5
        )
        if r.status_code == 200:
            log("✅ Firebase URL updated successfully.")
        else:
            log(f"Failed to update Firebase URL: {r.status_code} - {r.text}")
    except Exception as e:
        log(f"Firebase Update Error: {e}")

# ---------------------------------------------------------
# GUI
# ---------------------------------------------------------
class ServerApp:
    def __init__(self, root):
        global _gui_app
        _gui_app = self
        self.root = root
        self.root.title("SmartPower 자체 서버 v1.0")
        self.root.geometry("550x500")
        self.root.resizable(True, True)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # 헤더
        header = ctk.CTkFrame(root, fg_color="#1a1a2e", corner_radius=0)
        header.pack(fill="x", pady=0)
        ctk.CTkLabel(header, text="⚡ SmartPower 자체 서버", font=("Malgun Gothic", 18, "bold"), text_color="#60a5fa").pack(pady=10)

        # 상태 카드들
        stats_frame = ctk.CTkFrame(root)
        stats_frame.pack(fill="x", padx=15, pady=10)

        self.lbl_clients = ctk.CTkLabel(stats_frame, text="🖥️ 연결된 클라이언트: 0", font=("Malgun Gothic", 13))
        self.lbl_clients.pack(side="left", padx=20, pady=8)

        self.lbl_admins = ctk.CTkLabel(stats_frame, text="👤 관리자: 0", font=("Malgun Gothic", 13))
        self.lbl_admins.pack(side="left", padx=20, pady=8)

        # 서버 상태
        status_frame = ctk.CTkFrame(root)
        status_frame.pack(fill="x", padx=15, pady=5)

        self.lbl_port = ctk.CTkLabel(status_frame, text=f"🟢 서버 실행 중 (포트 {PORT})", font=("Malgun Gothic", 12), text_color="#34d399")
        self.lbl_port.pack(pady=5)

        self.lbl_tunnel = ctk.CTkLabel(status_frame, text="🟡 Cloudflare 터널: 연결 중...", font=("Malgun Gothic", 11), text_color="#fbbf24", wraplength=500)
        self.lbl_tunnel.pack(pady=5)

        # 로그
        ctk.CTkLabel(root, text="📋 실시간 로그", font=("Malgun Gothic", 12, "bold")).pack(anchor="w", padx=15, pady=(10, 2))
        self.log_box = ctk.CTkTextbox(root, font=("Consolas", 11), height=260)
        self.log_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.log_box.configure(state="disabled")

        self._update_gui()

    def update_tunnel_url(self, url):
        self.lbl_tunnel.configure(text=f"🟢 터널: {url}", text_color="#34d399")

    def _update_gui(self):
        try:
            client_count = len(_client_connections)
            admin_count = len(_admin_connections)
            self.lbl_clients.configure(text=f"🖥️ 연결된 클라이언트: {client_count}")
            self.lbl_admins.configure(text=f"👤 관리자: {admin_count}")

            # 로그 업데이트 (마지막 100개)
            current_log = self.log_box.get("1.0", "end").strip()
            new_log = "\n".join(_log_queue)
            if current_log != new_log:
                self.log_box.configure(state="normal")
                self.log_box.delete("1.0", "end")
                self.log_box.insert("end", new_log)
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
        except Exception:
            pass
        self.root.after(500, self._update_gui)

# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------
def main():
    # WebSocket 서버 스레드 시작
    ws_thread = threading.Thread(target=run_ws_server, daemon=True)
    ws_thread.start()

    # Cloudflare 터널 스레드 시작 (1초 딜레이 후)
    def start_tunnel():
        time.sleep(1)
        run_cloudflare_tunnel()

    tunnel_thread = threading.Thread(target=start_tunnel, daemon=True)
    tunnel_thread.start()

    # GUI 시작 (메인 스레드)
    root = ctk.CTk()
    app = ServerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
