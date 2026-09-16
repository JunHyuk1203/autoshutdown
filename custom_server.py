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
_pcs = {}              # pc_id -> {status payload}
_connections = {}      # type -> { ws -> { info } }
_connections['admin'] = {}
_connections['client'] = {}

# GUI Log Queue
_log_queue = []

# ---------------------------------------------------------
# UTILS & AUTH
# ---------------------------------------------------------
def log(msg):
    ts = time.strftime("%H:%M:%S")
    _log_queue.append(f"[{ts}] {msg}")
    print(f"[{ts}] {msg}")
    if len(_log_queue) > 100:
        _log_queue.pop(0)

def _get_google_public_keys():
    global _GOOGLE_KEYS, _GOOGLE_KEYS_EXPIRES
    now = time.time()
    if now < _GOOGLE_KEYS_EXPIRES and _GOOGLE_KEYS:
        return _GOOGLE_KEYS
    try:
        resp = requests.get("https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com", timeout=5)
        headers = resp.headers
        cache_control = headers.get('cache-control', '')
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
        # 클라이언트 PC는 별도의 인증 토큰을 요구하지 않음 (Firebase 규칙과 동일)
        return True, {"uid": "client", "email": "client", "role": "client"}
        
    decoded, err = _verify_firebase_token(token)
    if not decoded:
        return False, err
    
    email = decoded.get("email", "")
    uid = decoded.get("user_id", "")
    
    if email.lower() == MASTER_EMAIL.lower():
        return True, {"uid": uid, "email": email, "role": "admin"}
    
    # RTDB에서 승인 여부 조회
    try:
        r = requests.get(f"{FIREBASE_DB_URL}/users/{uid}.json", timeout=3)
        val = r.json()
        if val and val.get("approved") is True:
            return True, {"uid": uid, "email": email, "role": "admin"}
    except:
        pass
    return False, "Not approved admin"

# ---------------------------------------------------------
# WEBSOCKET SERVER
# ---------------------------------------------------------
async def _broadcast_to_admins(msg_dict):
    payload = json.dumps(msg_dict)
    aws = [asyncio.create_task(ws.send(payload)) for ws in _connections['admin'].keys()]
    if aws:
        await asyncio.wait(aws)

async def _send_to_client(pc_id, msg_dict):
    payload = json.dumps(msg_dict)
    aws = []
    for ws, info in _connections['client'].items():
        if info.get('pc_id') == pc_id:
            aws.append(asyncio.create_task(ws.send(payload)))
    if aws:
        await asyncio.wait(aws)

async def handler(ws, path):
    client_ip = ws.remote_address[0] if ws.remote_address else "Unknown"
    role = "unknown"
    pc_id = None
    
    try:
        # First message must be auth
        auth_msg_raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
        auth_msg = json.loads(auth_msg_raw)
        
        if auth_msg.get("type") == "auth":
            token = auth_msg.get("token")
            role_req = auth_msg.get("role", "client")
            is_valid, user_info = _check_auth(token, role_req)
            
            if not is_valid:
                await ws.send(json.dumps({"type": "auth_result", "status": "fail", "reason": user_info}))
                return
            
            role = user_info['role']
            if role == "client":
                pc_id = auth_msg.get("pc_id")
                if not pc_id:
                    await ws.send(json.dumps({"type": "auth_result", "status": "fail", "reason": "Missing pc_id"}))
                    return
                _connections['client'][ws] = {"pc_id": pc_id, "uid": user_info['uid']}
                log(f"Client Connected: {pc_id}")
            else:
                _connections['admin'][ws] = {"uid": user_info['uid'], "email": user_info['email']}
                log(f"Admin Connected: {user_info['email']}")
                # 관리자 접속 시 현재 전체 상태 전송
                await ws.send(json.dumps({"type": "full_state", "data": _pcs}))
                
            await ws.send(json.dumps({"type": "auth_result", "status": "success"}))
        else:
            return
            
    except Exception as e:
        log(f"Auth Error ({client_ip}): {e}")
        return

    # Main message loop
    try:
        async for message in ws:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if role == "client":
                if msg_type == "status":
                    # Update state
                    payload = data.get("payload", {})
                    _pcs[pc_id] = payload
                    # Broadcast to admins
                    await _broadcast_to_admins({"type": "pc_update", "pc_id": pc_id, "data": payload})
                    
            elif role == "admin":
                if msg_type == "command":
                    target_pc = data.get("target_pc")
                    action = data.get("action")
                    cmd_payload = data.get("payload", {})
                    
                    log(f"Command from {user_info['email']}: {action} -> {target_pc}")
                    cmd_msg = {"type": "command", "action": action, "payload": cmd_payload}
                    
                    if target_pc == "__ALL__":
                        # Send to all clients
                        payload_str = json.dumps(cmd_msg)
                        aws = [asyncio.create_task(c_ws.send(payload_str)) for c_ws in _connections['client'].keys()]
                        if aws: await asyncio.wait(aws)
                    else:
                        await _send_to_client(target_pc, cmd_msg)
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        log(f"WS Error ({client_ip}): {e}")
    finally:
        if role == "client":
            if ws in _connections['client']:
                del _connections['client'][ws]
                log(f"Client Disconnected: {pc_id}")
                if pc_id in _pcs:
                    _pcs[pc_id]['status'] = 'offline'
                    asyncio.create_task(_broadcast_to_admins({"type": "pc_update", "pc_id": pc_id, "data": _pcs[pc_id]}))
        elif role == "admin":
            if ws in _connections['admin']:
                del _connections['admin'][ws]
                log(f"Admin Disconnected: {user_info.get('email', 'Unknown')}")

async def main_ws():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        log(f"WebSocket Server started on port {PORT}")
        await asyncio.Future()  # run forever

def run_ws_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_ws())

# ---------------------------------------------------------
# CLOUDFLARE TUNNEL
# ---------------------------------------------------------
_tunnel_url = ""

def run_cloudflare_tunnel():
    global _tunnel_url
    log("Starting Cloudflare Tunnel...")
    
    # Try to find cloudflared
    cf_path = "cloudflared.exe"
    if getattr(sys, 'frozen', False):
        cf_path = os.path.join(sys._MEIPASS, "cloudflared.exe")
    else:
        cf_path = os.path.join(os.path.dirname(__file__), "cloudflared.exe")

    if not os.path.exists(cf_path):
        log(f"WARNING: {cf_path} not found! Tunnel won't start.")
        return
        
    cmd = [cf_path, "tunnel", "--url", f"http://localhost:{PORT}"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for line in iter(proc.stdout.readline, ''):
            line = line.strip()
            if "https://" in line and "trycloudflare.com" in line:
                match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
                if match:
                    raw_url = match.group(1)
                    _tunnel_url = raw_url.replace("https://", "wss://")
                    log(f"Tunnel Established: {_tunnel_url}")
                    update_firebase_url(_tunnel_url)
    except Exception as e:
        log(f"Tunnel Error: {e}")

def update_firebase_url(url):
    try:
        r = requests.put(f"{FIREBASE_DB_URL}/update_info/custom_server_url.json", json=url, timeout=5)
        if r.status_code == 200:
            log("Firebase URL updated successfully.")
        else:
            log(f"Failed to update Firebase URL: {r.status_code}")
    except Exception as e:
        log(f"Firebase Update Error: {e}")

# ---------------------------------------------------------
# GUI
# ---------------------------------------------------------
class ServerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SmartPower 자체 서버 (v1.0.0)")
        self.root.geometry("450x450")
        
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        # UI Elements
        self.lbl_status = ctk.CTkLabel(root, text="🟢 서버 상태: 실행 중 (포트 8765)", font=("Malgun Gothic", 14, "bold"))
        self.lbl_status.pack(pady=(10, 5))
        
        self.lbl_tunnel = ctk.CTkLabel(root, text="☀️ Cloudflare Tunnel: 대기 중...", text_color="#F39C12", font=("Malgun Gothic", 12))
        self.lbl_tunnel.pack(pady=0)
        
        frame_stats = ctk.CTkFrame(root)
        frame_stats.pack(fill="x", padx=10, pady=10)
        
        self.lbl_clients = ctk.CTkLabel(frame_stats, text="📡 연결된 PC 클라이언트: 0개", font=("Malgun Gothic", 12))
        self.lbl_clients.pack(anchor="w", padx=10, pady=2)
        
        self.lbl_admins = ctk.CTkLabel(frame_stats, text="🌐 연결된 관리 웹: 0개", font=("Malgun Gothic", 12))
        self.lbl_admins.pack(anchor="w", padx=10, pady=2)
        
        self.txt_log = ctk.CTkTextbox(root, state="disabled", font=("Consolas", 11))
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=5)
        
        btn_frame = ctk.CTkFrame(root, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        self.btn_clear = ctk.CTkButton(btn_frame, text="로그 지우기", command=self.clear_log)
        self.btn_clear.pack(side="right")
        
        self.update_ui()
        
    def clear_log(self):
        global _log_queue
        _log_queue.clear()
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")

    def update_ui(self):
        # Update tunnel label
        global _tunnel_url
        if _tunnel_url:
            self.lbl_tunnel.configure(text=f"☀️ Cloudflare Tunnel: {_tunnel_url}", text_color="#2ECC71")
        
        # Update stats
        self.lbl_clients.configure(text=f"📡 연결된 PC 클라이언트: {len(_connections['client'])}개")
        self.lbl_admins.configure(text=f"🌐 연결된 관리 웹: {len(_connections['admin'])}개")
        
        # Update log
        self.txt_log.configure(state="normal")
        curr_text = self.txt_log.get("1.0", "end").strip()
        lines = curr_text.split("\n") if curr_text else []
        
        if len(lines) != len(_log_queue) or (lines and _log_queue and lines[-1] != _log_queue[-1]):
            self.txt_log.delete("1.0", "end")
            self.txt_log.insert("end", "\n".join(_log_queue) + "\n")
            self.txt_log.see("end")
        
        self.txt_log.configure(state="disabled")
        
        self.root.after(1000, self.update_ui)

def run_gui():
    root = ctk.CTk()
    app = ServerApp(root)
    root.mainloop()
    os._exit(0)

if __name__ == "__main__":
    t_ws = threading.Thread(target=run_ws_server, daemon=True)
    t_ws.start()
    
    t_tunnel = threading.Thread(target=run_cloudflare_tunnel, daemon=True)
    t_tunnel.start()
    
    run_gui()
