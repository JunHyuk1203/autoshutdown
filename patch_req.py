import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

# Add requests import
if "import requests" not in text:
    text = text.replace("import urllib.parse\n", "import urllib.parse\nimport requests\nimport urllib3\nurllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)\n")

# Replace urllib in GUI http_poller_thread
target_gui = """                # 1. 내 PC 상태 보고 (PATCH)
                now_ts = time.time()
                if not hasattr(self, 'last_status_update'): self.last_status_update = 0
                if now_ts - self.last_status_update >= 5.0:
                    self.last_status_update = now_ts
                
                    current_vol = 50
                    if PYCAW_AVAILABLE:
                        try:
                            _devs = AudioUtilities.GetSpeakers()
                            _vol_intf = _devs.EndpointVolume
                            current_vol = int(_vol_intf.GetMasterVolumeLevelScalar() * 100)
                        except:
                            pass
                    status_payload = json.dumps({
                        'volume': current_vol,
                        'ip': ip,
                        'mac': '',
                        'hostname': socket.gethostname(),
                        'user': current_user,
                        'version': CURRENT_VERSION,
                        'status': 'online',
                        'next_event': next_str,
                        'last_seen': datetime.now().strftime('%H:%M:%S'),
                        'last_seen_ts': {'.sv': 'timestamp'},
                        'config': current_cfg,
                        'windows': get_open_windows()
                    }).encode('utf-8')
                
                    patch_url = f"{central_url.rstrip('/')}/pcs/{pc_id}.json"
                    patch_req = urllib.request.Request(
                        patch_url, 
                        data=status_payload, 
                        method='PATCH', 
                        headers={
                            'Content-Type': 'application/json',
                            'Content-Length': str(len(status_payload))
                        }
                    )
                    try:
                        with urllib.request.urlopen(patch_req, timeout=10, context=ssl_context) as res:
                            pass
                    except urllib.error.HTTPError as he:
                        try:
                            err_body = he.read().decode('utf-8', errors='replace')
                            with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                ef.write(f"[{datetime.now()}] PUT error: {he.code} {he.reason} | URL: {patch_url} | Body: {err_body}\\n")
                        except: pass
                    except Exception as e:
                        try:
                            with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                ef.write(f"[{datetime.now()}] PUT error: {e}\\n")
                        except: pass
                
                # 2. 다른 PC 목록 가져오기 (비활성화 - Firebase 직접 연동)
                
                # 3. 대기 중인 명령 확인 (GET)
                cmd = None
                cmd_type = None
                
                # 개별 명령 조회
                cmd_url = f"{central_url.rstrip('/')}/commands/{pc_id}.json"
                cmd_req = urllib.request.Request(cmd_url, method='GET')
                try:
                    with urllib.request.urlopen(cmd_req, timeout=6, context=ssl_context) as res:
                        cmd = json.loads(res.read().decode('utf-8'))
                        if cmd:
                            cmd_type = 'individual'
                except Exception as e:
                    try:
                        with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                            ef.write(f"[{datetime.now()}] GET cmd error: {e}\\n")
                    except: pass
                        
                # 개별 명령이 없으면 전체 명령 조회
                if not cmd:
                    now_ts = time.time()
                    if not hasattr(self, 'last_all_cmd_check'): self.last_all_cmd_check = 0
                    if now_ts - self.last_all_cmd_check >= 5.0:
                        self.last_all_cmd_check = now_ts
                        all_cmd_url = f"{central_url.rstrip('/')}/commands/__ALL__.json"
                        all_cmd_req = urllib.request.Request(all_cmd_url, method='GET')
                        try:
                            with urllib.request.urlopen(all_cmd_req, timeout=6, context=ssl_context) as res:
                                cmd = json.loads(res.read().decode('utf-8'))
                                if cmd:
                                    cmd_type = 'all'
                                    cmd_ts = cmd.get('timestamp', 0)
                                    if cmd_ts == getattr(self, 'last_all_cmd_ts', 0) or time.time() - cmd_ts > 300.0:
                                        cmd = None
                                    else:
                                        self.last_all_cmd_ts = cmd_ts
                        except Exception as e:
                            try:
                                with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                    ef.write(f"[{datetime.now()}] GET all cmd error: {e}\\n")
                            except: pass"""

replacement_gui = """                # Requests Session setup for Keep-Alive
                if not hasattr(self, 'http_session'):
                    self.http_session = requests.Session()
                    self.http_session.verify = False

                # 1. 내 PC 상태 보고 (PATCH)
                now_ts = time.time()
                if not hasattr(self, 'last_status_update'): self.last_status_update = 0
                if now_ts - self.last_status_update >= 5.0:
                    self.last_status_update = now_ts
                
                    current_vol = 50
                    if PYCAW_AVAILABLE:
                        try:
                            _devs = AudioUtilities.GetSpeakers()
                            _vol_intf = _devs.EndpointVolume
                            current_vol = int(_vol_intf.GetMasterVolumeLevelScalar() * 100)
                        except:
                            pass
                    status_payload = {
                        'volume': current_vol,
                        'ip': ip,
                        'mac': '',
                        'hostname': socket.gethostname(),
                        'user': current_user,
                        'version': CURRENT_VERSION,
                        'status': 'online',
                        'next_event': next_str,
                        'last_seen': datetime.now().strftime('%H:%M:%S'),
                        'last_seen_ts': {'.sv': 'timestamp'},
                        'config': current_cfg,
                        'windows': get_open_windows()
                    }
                
                    patch_url = f"{central_url.rstrip('/')}/pcs/{pc_id}.json"
                    try:
                        self.http_session.patch(patch_url, json=status_payload, timeout=10)
                    except Exception as e:
                        try:
                            with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                ef.write(f"[{datetime.now()}] PUT error: {e}\\n")
                        except: pass
                
                # 3. 대기 중인 명령 확인 (GET)
                cmd = None
                cmd_type = None
                
                # 개별 명령 조회
                cmd_url = f"{central_url.rstrip('/')}/commands/{pc_id}.json"
                try:
                    res = self.http_session.get(cmd_url, timeout=6)
                    if res.status_code == 200:
                        cmd = res.json()
                        if cmd:
                            cmd_type = 'individual'
                except Exception as e:
                    pass
                        
                # 개별 명령이 없으면 전체 명령 조회 (5초 간격으로 제한하여 트래픽 최소화)
                if not cmd:
                    now_ts = time.time()
                    if not hasattr(self, 'last_all_cmd_check'): self.last_all_cmd_check = 0
                    if now_ts - self.last_all_cmd_check >= 5.0:
                        self.last_all_cmd_check = now_ts
                        all_cmd_url = f"{central_url.rstrip('/')}/commands/__ALL__.json"
                        try:
                            res = self.http_session.get(all_cmd_url, timeout=6)
                            if res.status_code == 200:
                                cmd = res.json()
                                if cmd:
                                    cmd_type = 'all'
                                    cmd_ts = cmd.get('timestamp', 0)
                                    if cmd_ts == getattr(self, 'last_all_cmd_ts', 0) or time.time() - cmd_ts > 300.0:
                                        cmd = None
                                    else:
                                        self.last_all_cmd_ts = cmd_ts
                        except Exception as e:
                            pass"""

if target_gui in text:
    text = text.replace(target_gui, replacement_gui)
else:
    print("Failed to replace GUI polling loop! Trying a more flexible regex...")
    # Oh wait, my patch earlier changed the block, wait:
    # I didn't change the GET ALL CMD block in patch_final.py! It's still `if not cmd: all_cmd_url ...`
    pass

# Deletion block for GUI
target_del_gui = """                        if cmd_success and cmd_type == 'individual':
                            if push_id:
                                del_url = f"{central_url.rstrip('/')}/commands/{pc_id}/{push_id}.json"
                            else:
                                                        del_url = f"{central_url.rstrip('/')}/commands/{pc_id}.json"
                            del_req = urllib.request.Request(del_url, method='DELETE')
                            try:
                                with urllib.request.urlopen(del_req, timeout=6, context=ssl_context) as res:
                                    pass
                            except Exception as e:
                                try:
                                    with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                        ef.write(f"[{datetime.now()}] DELETE cmd error: {e}\\n")
                                except: pass
                            # 강제로 다음 루프에서 상태 업데이트를 하도록 시간 초기화
                            self.last_status_update = 0"""

replacement_del_gui = """                        if cmd_success and cmd_type == 'individual':
                            if push_id:
                                del_url = f"{central_url.rstrip('/')}/commands/{pc_id}/{push_id}.json"
                            else:
                                del_url = f"{central_url.rstrip('/')}/commands/{pc_id}.json"
                            try:
                                self.http_session.delete(del_url, timeout=6)
                            except Exception as e:
                                pass
                            # 강제로 다음 루프에서 상태 업데이트를 하도록 시간 초기화
                            self.last_status_update = 0"""

if target_del_gui in text:
    text = text.replace(target_del_gui, replacement_del_gui)
else:
    print("Failed to replace GUI del loop")


with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Done patching.")
