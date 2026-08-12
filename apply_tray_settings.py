import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Remove the AutoLogin frame from settings_tab
start_marker = "        # 자동 로그인(부팅 시) 프레임"
end_marker = "        # 시작프로그램 등록 프레임"
idx_start = text.find(start_marker)
idx_end = text.find(end_marker)

if idx_start != -1 and idx_end != -1:
    text = text[:idx_start] + text[idx_end:]
    print("Removed AutoLogin frame from settings")
else:
    print("Could not find AutoLogin frame!")

# 2. Change apply_auto_unlock and _toggle_unlock_entry to be part of the new Tray Dialog
# Wait, let's just rewrite the entire block for the Tray Dialog and remove the old ones.
old_funcs_start = "    def _toggle_unlock_entry(self):"
old_funcs_end = "    def toggle_startup(self):"
idx_funcs_start = text.find(old_funcs_start)
idx_funcs_end = text.find(old_funcs_end)

if idx_funcs_start != -1 and idx_funcs_end != -1:
    text = text[:idx_funcs_start] + text[idx_funcs_end:]
    print("Removed old toggle/apply functions")
else:
    print("Could not find old toggle/apply functions")


# 3. Add new tray functions (open_autologin_settings, restart_as_admin) to AutoShutdownApp class
new_funcs = """
    def restart_as_admin(self, icon=None, item=None):
        if ctypes.windll.shell32.IsUserAnAdmin():
            messagebox.showinfo("알림", "이미 관리자 권한으로 실행 중입니다.")
            return
        try:
            import ctypes, sys
            if getattr(sys, 'frozen', False):
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
            else:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join([sys.argv[0]] + sys.argv[1:]), None, 1)
            if self.icon:
                self.icon.stop()
            self.root.quit()
        except Exception as e:
            pass

    def open_autologin_settings(self, icon=None, item=None):
        # Create a new TopLevel window
        top = tk.Toplevel(self.root)
        top.title("부팅 시 자동 로그인 설정")
        top.geometry("380x180")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        
        # Center the window
        top.update_idletasks()
        x = (top.winfo_screenwidth() - 380) // 2
        y = (top.winfo_screenheight() - 180) // 2
        top.geometry(f"+{x}+{y}")

        frame = ttk.Frame(top, padding=15)
        frame.pack(fill="both", expand=True)

        auto_unlock_var = tk.BooleanVar(value=self.current_cfg.get('auto_unlock_enabled', False))
        
        def toggle_entry():
            if auto_unlock_var.get():
                password_entry.config(state="normal")
            else:
                password_entry.config(state="disabled")

        chk = ttk.Checkbutton(frame, text="부팅 시 자동으로 잠금 해제 켜기", variable=auto_unlock_var, command=toggle_entry)
        chk.pack(anchor="w", pady=(0, 15))

        pwd_frame = ttk.Frame(frame)
        pwd_frame.pack(fill="x", pady=5)
        ttk.Label(pwd_frame, text="Windows 비밀번호:").pack(side="left")
        password_entry = ttk.Entry(pwd_frame, show="*")
        password_entry.pack(side="left", fill="x", expand=True, padx=5)

        saved_enc_pwd = self.current_cfg.get('encrypted_password', "")
        if saved_enc_pwd:
            password_entry.insert(0, decrypt_password(saved_enc_pwd))
            
        toggle_entry()

        def apply_settings():
            enabled = auto_unlock_var.get()
            pwd = password_entry.get()
            
            if not ctypes.windll.shell32.IsUserAnAdmin():
                messagebox.showwarning("권한 필요", "자동 로그인을 설정하려면 관리자 권한이 필요합니다.\\n트레이 메뉴에서 '관리자 권한으로 열기'를 사용해주세요.", parent=top)
                return
                
            import getpass
            username = getpass.getuser()
            
            if enabled:
                if not pwd:
                    messagebox.showerror("오류", "비밀번호를 입력해주세요.", parent=top)
                    return
                if set_auto_logon(username, pwd):
                    self.current_cfg['auto_unlock_enabled'] = True
                    self.current_cfg['encrypted_password'] = encrypt_password(pwd)
                    self.save_config()
                    messagebox.showinfo("성공", "자동 로그인이 활성화되었습니다.\\n(다음 부팅 시부터 적용됩니다)", parent=top)
                    top.destroy()
                else:
                    messagebox.showerror("오류", "레지스트리 설정에 실패했습니다.", parent=top)
            else:
                if disable_auto_logon():
                    self.current_cfg['auto_unlock_enabled'] = False
                    self.current_cfg['encrypted_password'] = ""
                    self.save_config()
                    messagebox.showinfo("성공", "자동 로그인이 비활성화되었습니다.", parent=top)
                    top.destroy()
                else:
                    messagebox.showerror("오류", "레지스트리 설정에 실패했습니다.", parent=top)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(15, 0))
        
        apply_btn = ttk.Button(btn_frame, text="적용 (관리자 권한 필요)", command=apply_settings)
        apply_btn.pack(side="right")
        cancel_btn = ttk.Button(btn_frame, text="닫기", command=top.destroy)
        cancel_btn.pack(side="right", padx=5)

"""
insert_target = "    def toggle_startup(self):"
text = text.replace(insert_target, new_funcs + insert_target)

# 4. Add the menu items to the tray
tray_menu_target = "            pystray.MenuItem('오늘 하루 끄지 않기', self.toggle_skip_state, checked=self.get_skip_state),"
tray_menu_code = """            pystray.MenuItem('관리자 권한으로 열기', self.restart_as_admin, visible=lambda item: not ctypes.windll.shell32.IsUserAnAdmin()),
            pystray.MenuItem('부팅 시 자동로그인 설정', self.open_autologin_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('오늘 하루 끄지 않기', self.toggle_skip_state, checked=self.get_skip_state),"""
text = text.replace(tray_menu_target, tray_menu_code)

text = text.replace('CURRENT_VERSION = "1.1.144"', 'CURRENT_VERSION = "1.1.145"')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Updated auto_shutdown.py")

with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = re.sub(r'1\.1\.14[34]', '1.1.145', vtext)
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)

print("Version bumped to 1.1.145")
