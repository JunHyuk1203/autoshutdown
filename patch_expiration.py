import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

target_code = """                    for push_id, payload in commands_to_process:
                        action = payload.get("action")
                        message = payload.get("message", "")
                    
                        # 진단 로그: 명령 수신 기록"""

replacement_code = """                    for push_id, payload in commands_to_process:
                        action = payload.get("action")
                        message = payload.get("message", "")
                        
                        # 10초 이상 지난 오래된 명령 무시 및 삭제
                        cmd_ts = payload.get("timestamp", 0)
                        if cmd_ts > 0 and time.time() - cmd_ts > 10.0:
                            cmd_success = True
                            continue
                    
                        # 진단 로그: 명령 수신 기록"""

if target_code in text:
    text = text.replace(target_code, replacement_code)
    print("Added 10s expiration to GUI")

target_code_headless = """                    for push_id, payload in commands_to_process:
                        action = payload.get("action")
                        message = payload.get("message", "")
                        _log(f"Executing cmd: action={action}")"""

replacement_code_headless = """                    for push_id, payload in commands_to_process:
                        action = payload.get("action")
                        message = payload.get("message", "")
                        
                        # 10초 이상 지난 오래된 명령 무시 및 삭제
                        cmd_ts = payload.get("timestamp", 0)
                        if cmd_ts > 0 and time.time() - cmd_ts > 10.0:
                            cmd_success = True
                            _log(f"Ignored stale cmd: action={action} (older than 10s)")
                            continue
                            
                        _log(f"Executing cmd: action={action}")"""

if target_code_headless in text:
    text = text.replace(target_code_headless, replacement_code_headless)
    print("Added 10s expiration to Headless")

text = text.replace('CURRENT_VERSION = "1.1.136"', 'CURRENT_VERSION = "1.1.137"')
text = text.replace('CURRENT_VERSION = "1.1.135"', 'CURRENT_VERSION = "1.1.137"')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = re.sub(r'1\.1\.13[56]', '1.1.137', vtext)
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)
