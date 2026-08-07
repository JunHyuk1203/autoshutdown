import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. For GUI mode
target_del_gui = """                            del_req = urllib.request.Request(del_url, method='DELETE')
                            try:
                                with urllib.request.urlopen(del_req, timeout=6, context=ssl_context) as res:
                                    pass
                            except Exception as e:
                                try:
                                    with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                        ef.write(f"[{datetime.now()}] DELETE cmd error: {e}\\n")
                                except: pass"""

replacement_del_gui = target_del_gui + """
                            # 강제로 다음 루프에서 상태 업데이트를 하도록 시간 초기화
                            self.last_status_update = 0"""

if target_del_gui in text:
    text = text.replace(target_del_gui, replacement_del_gui)

# 2. For Headless mode
target_del_headless = """                            del_req = urllib.request.Request(del_url, method='DELETE', headers={'User-Agent': 'Mozilla/5.0'})
                            try:
                                with urllib.request.urlopen(del_req, timeout=5, context=ssl_context) as res:
                                    pass
                                _log("CMD deleted from Firebase")
                            except Exception as de:
                                _log(f"CMD delete error: {de}")"""

replacement_del_headless = target_del_headless + """
                            # 강제로 다음 루프에서 상태 업데이트를 하도록 시간 초기화
                            self.last_status_update = 0"""

if target_del_headless in text:
    text = text.replace(target_del_headless, replacement_del_headless)

text = text.replace('CURRENT_VERSION = "1.1.130"', 'CURRENT_VERSION = "1.1.131"')
text = text.replace('CURRENT_VERSION = "1.1.129"', 'CURRENT_VERSION = "1.1.131"')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = re.sub(r'1\.1\.130', '1.1.131', vtext)
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)

print("auto_shutdown.py patched for instant status update!")
