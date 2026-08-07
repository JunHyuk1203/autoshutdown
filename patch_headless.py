import sys

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

# Add missing commands to headless mode
target_block = """                            elif action == 'close_active_window':
                                _log("Executing: close active window")
                                try:
                                    hwnd = ctypes.windll.user32.GetForegroundWindow()
                                    if hwnd:
                                        length = 256
                                        class_name = ctypes.create_unicode_buffer(length)
                                        ctypes.windll.user32.GetClassNameW(hwnd, class_name, length)
                                        if class_name.value not in ["Progman", "WorkerW", "Shell_TrayWnd"]:
                                            ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)
                                except Exception as close_ex:
                                    _log(f"close_active_window error: {close_ex}")
                                cmd_success = True"""

missing_commands = """
                            elif action == 'kill_process' and isinstance(message, dict):
                                target_pid = message.get('pid')
                                target_exe = message.get('exe', '')
                                target_hwnd = message.get('hwnd')
                                if target_pid:
                                    if target_exe == 'explorer.exe' and target_hwnd:
                                        try:
                                            target_hwnd_int = int(target_hwnd)
                                            ctypes.windll.user32.PostMessageW(target_hwnd_int, 0x0010, 0, 0)
                                        except Exception: pass
                                    else:
                                        os.system(f'taskkill /F /PID {target_pid}')
                                    cmd_success = True
                            elif action == 'bring_to_front' and isinstance(message, dict):
                                target_hwnd = message.get('hwnd')
                                if target_hwnd:
                                    try:
                                        target_hwnd_int = int(target_hwnd)
                                        ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
                                        ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
                                        if ctypes.windll.user32.IsIconic(target_hwnd_int):
                                            ctypes.windll.user32.ShowWindow(target_hwnd_int, 9)
                                        else:
                                            ctypes.windll.user32.ShowWindow(target_hwnd_int, 5)
                                        ctypes.windll.user32.SetForegroundWindow(target_hwnd_int)
                                    except Exception: pass
                                    cmd_success = True
                            elif action == 'minimize_window' and isinstance(message, dict):
                                target_hwnd = message.get('hwnd')
                                if target_hwnd:
                                    try:
                                        target_hwnd_int = int(target_hwnd)
                                        ctypes.windll.user32.ShowWindow(target_hwnd_int, 6)
                                    except Exception: pass
                                    cmd_success = True
                            elif action == 'maximize_window' and isinstance(message, dict):
                                target_hwnd = message.get('hwnd')
                                if target_hwnd:
                                    try:
                                        target_hwnd_int = int(target_hwnd)
                                        ctypes.windll.user32.ShowWindow(target_hwnd_int, 3)
                                        ctypes.windll.user32.SetForegroundWindow(target_hwnd_int)
                                    except Exception: pass
                                    cmd_success = True
                            elif action == 'restore_window' and isinstance(message, dict):
                                target_hwnd = message.get('hwnd')
                                if target_hwnd:
                                    try:
                                        target_hwnd_int = int(target_hwnd)
                                        ctypes.windll.user32.ShowWindow(target_hwnd_int, 9)
                                        ctypes.windll.user32.SetForegroundWindow(target_hwnd_int)
                                    except Exception: pass
                                    cmd_success = True
                            elif action == 'close_window' and isinstance(message, dict):
                                target_hwnd = message.get('hwnd')
                                if target_hwnd:
                                    try:
                                        target_hwnd_int = int(target_hwnd)
                                        ctypes.windll.user32.PostMessageW(target_hwnd_int, 0x0010, 0, 0)
                                    except Exception: pass
                                    cmd_success = True
                            elif action == 'open_file' and isinstance(message, dict):
                                file_path = message.get('file_path', '').strip()
                                app_path  = message.get('app_path', '').strip()
                                if file_path:
                                    try:
                                        is_url = file_path.lower().startswith(('http://', 'https://', 'ftp://'))
                                        if app_path:
                                            subprocess.Popen([app_path, file_path], creationflags=subprocess.CREATE_NO_WINDOW)
                                        elif is_url:
                                            subprocess.Popen(['cmd', '/c', 'start', '', file_path], creationflags=subprocess.CREATE_NO_WINDOW)
                                        else:
                                            os.startfile(file_path)
                                        cmd_success = True
                                    except Exception: pass"""

if target_block in text:
    text = text.replace(target_block, target_block + missing_commands)
    
# Fix message in headless
target_msg_headless = """                            elif action == 'message':
                                # headless 모드에서는 팝업 표시 불가 → 명령만 소비(삭제)
                                _log(f"message received in headless - acknowledging: {message}")
                                cmd_success = True"""

replacement_msg_headless = """                            elif action == 'message':
                                _log(f"message received in headless - showing ctypes messagebox: {message}")
                                try:
                                    import ctypes
                                    import threading
                                    threading.Thread(target=lambda m=message: ctypes.windll.user32.MessageBoxW(0, m, "관리자 메시지", 0x40000), daemon=True).start()
                                except Exception as e:
                                    _log(f"headless message error: {e}")
                                cmd_success = True"""

if target_msg_headless in text:
    text = text.replace(target_msg_headless, replacement_msg_headless)

# Also bump version again to 125 so deploy script catches it
text = text.replace('CURRENT_VERSION = "1.1.124"', 'CURRENT_VERSION = "1.1.125"')
text = text.replace('CURRENT_VERSION = "1.1.123"', 'CURRENT_VERSION = "1.1.125"')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = vtext.replace('1.1.124', '1.1.125').replace('1.1.123', '1.1.125')
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)

print("auto_shutdown.py updated for headless missing features, bumped to 125")
