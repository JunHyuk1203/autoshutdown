import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

# Add crypto functions and registry functions at the top after imports
imports_target = "import sys"
imports_code = """import sys
import base64
import winreg
import getpass

def _get_encryption_key():
    import uuid
    mac = str(uuid.getnode())
    return [ord(c) for c in mac]

def encrypt_password(password):
    if not password: return ""
    key = _get_encryption_key()
    encrypted = bytearray()
    for i, c in enumerate(password.encode('utf-8')):
        encrypted.append(c ^ key[i % len(key)])
    return base64.b64encode(encrypted).decode('utf-8')

def decrypt_password(encrypted_b64):
    if not encrypted_b64: return ""
    try:
        key = _get_encryption_key()
        encrypted = base64.b64decode(encrypted_b64)
        decrypted = bytearray()
        for i, c in enumerate(encrypted):
            decrypted.append(c ^ key[i % len(key)])
        return decrypted.decode('utf-8')
    except Exception:
        return ""

def set_auto_logon(username, password):
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "AutoAdminLogon", 0, winreg.REG_SZ, "1")
        winreg.SetValueEx(key, "DefaultUserName", 0, winreg.REG_SZ, username)
        if password:
            winreg.SetValueEx(key, "DefaultPassword", 0, winreg.REG_SZ, password)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"set_auto_logon error: {e}")
        return False

def disable_auto_logon():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "AutoAdminLogon", 0, winreg.REG_SZ, "0")
        try:
            winreg.DeleteValue(key, "DefaultPassword")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"disable_auto_logon error: {e}")
        return False
"""
text = text.replace(imports_target, imports_code)


# Add settings UI in create_settings_tab
# Find where settings are built
settings_target = """        # 시작프로그램 등록 프레임
        startup_frame = ttk.Frame(container)"""
settings_code = """        # 자동 로그인(부팅 시) 프레임
        autologin_frame = ttk.LabelFrame(container, text="자동 로그인 (부팅 시 잠금 해제)", padding=10)
        autologin_frame.pack(fill="x", pady=5)
        
        self.auto_unlock_var = tk.BooleanVar(value=self.current_cfg.get('auto_unlock_enabled', False))
        chk_unlock = ttk.Checkbutton(autologin_frame, text="부팅 시 자동으로 잠금 해제 켜기", variable=self.auto_unlock_var, command=self._toggle_unlock_entry)
        chk_unlock.pack(anchor="w", pady=(0, 5))
        
        pwd_frame = ttk.Frame(autologin_frame)
        pwd_frame.pack(fill="x", pady=2)
        ttk.Label(pwd_frame, text="Windows 비밀번호:").pack(side="left")
        self.password_entry = ttk.Entry(pwd_frame, show="*")
        self.password_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # 복호화해서 채워두기 (화면엔 안 보이게 * 처리됨)
        saved_enc_pwd = self.current_cfg.get('encrypted_password', "")
        if saved_enc_pwd:
            self.password_entry.insert(0, decrypt_password(saved_enc_pwd))
            
        self.apply_unlock_btn = ttk.Button(autologin_frame, text="적용 (관리자 권한 필요)", command=self.apply_auto_unlock)
        self.apply_unlock_btn.pack(anchor="e", pady=(5,0))
        
        self._toggle_unlock_entry()

        # 시작프로그램 등록 프레임
        startup_frame = ttk.Frame(container)"""
text = text.replace(settings_target, settings_code)

# Add method to toggle unlock entry and apply unlock
class_end_target = """    def toggle_startup(self):"""
class_end_code = """    def _toggle_unlock_entry(self):
        if self.auto_unlock_var.get():
            self.password_entry.config(state="normal")
        else:
            self.password_entry.config(state="disabled")

    def apply_auto_unlock(self):
        enabled = self.auto_unlock_var.get()
        pwd = self.password_entry.get()
        
        if not ctypes.windll.shell32.IsUserAnAdmin():
            messagebox.showwarning("권한 필요", "자동 로그인을 설정하려면 관리자 권한으로 실행해야 합니다.\n설정 탭 상단의 '관리자 권한으로 재시작' 버튼을 이용해주세요.")
            # 원래 상태로 되돌림
            self.auto_unlock_var.set(self.current_cfg.get('auto_unlock_enabled', False))
            self._toggle_unlock_entry()
            return
            
        username = getpass.getuser()
        
        if enabled:
            if not pwd:
                messagebox.showerror("오류", "비밀번호를 입력해주세요.")
                self.auto_unlock_var.set(False)
                self._toggle_unlock_entry()
                return
            if set_auto_logon(username, pwd):
                self.current_cfg['auto_unlock_enabled'] = True
                self.current_cfg['encrypted_password'] = encrypt_password(pwd)
                self.save_config()
                messagebox.showinfo("성공", "자동 로그인이 활성화되었습니다.\\n(다음 부팅 시부터 적용됩니다)")
            else:
                messagebox.showerror("오류", "레지스트리 설정에 실패했습니다.")
        else:
            if disable_auto_logon():
                self.current_cfg['auto_unlock_enabled'] = False
                self.current_cfg['encrypted_password'] = ""
                self.password_entry.delete(0, 'end')
                self.save_config()
                messagebox.showinfo("성공", "자동 로그인이 비활성화되었습니다.")
            else:
                messagebox.showerror("오류", "레지스트리 설정에 실패했습니다.")

    def toggle_startup(self):"""
text = text.replace(class_end_target, class_end_code)

# Add remote unlock command handling
command_target = """                        elif action == 'close_active_window':"""
command_code = """                        elif action == 'unlock_screen':
                            # 원격 잠금 해제 시도 (화면 깨우기)
                            try:
                                ctypes.windll.user32.mouse_event(0x0001, 0, 0, 0, 0)
                                ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0) # Enter down
                                ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0) # Enter up
                                
                                if app_instance:
                                    app_instance.root.after(0, lambda: app_instance.add_system_alert("🔓 화면 깨우기 및 잠금해제 시도"))
                            except Exception as ex:
                                try:
                                    with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                        ef.write(f"[{datetime.now()}] unlock_screen FAILED: {ex}\\n")
                                except: pass
                            # cmd_success를 True로 안해줘도 개별명령은 무조건 지워지도록 패치되어 있으나, 성공 로깅을 위해
                            cmd_success = True
                            
                        elif action == 'close_active_window':"""
text = text.replace(command_target, command_code)

# Also add for headless mode
headless_command_target = """                            elif action == 'close_active_window':"""
headless_command_code = """                            elif action == 'unlock_screen':
                                try:
                                    ctypes.windll.user32.mouse_event(0x0001, 0, 0, 0, 0)
                                    ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
                                    ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)
                                except: pass
                                cmd_success = True
                            elif action == 'close_active_window':"""
text = text.replace(headless_command_target, headless_command_code)

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Patched auto_shutdown.py")
