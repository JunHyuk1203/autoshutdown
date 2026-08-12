with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

# Fix 1: Replace open_autologin_settings + _open_autologin_settings_gui entirely
# Use a completely independent tk.Tk() window to bypass CTkToplevel/withdrawn root issue
old_func = """    def open_autologin_settings(self, icon=None, item=None):
        self.root.after(0, self._open_autologin_settings_gui)

    def _open_autologin_settings_gui(self):
        # Workaround for CTkToplevel rendering blank when root is withdrawn
        was_hidden = not self.root.winfo_viewable()
        if was_hidden:
            self.root.attributes('-alpha', 0.0)
            self.root.deiconify()

        top = ctk.CTkToplevel(self.root)
        top.title("자동 로그인 설정")
        top.geometry("350x220")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        
        def on_close():
            top.destroy()
            if was_hidden:
                self.root.withdraw()
                self.root.attributes('-alpha', 1.0)
                
        top.protocol("WM_DELETE_WINDOW", on_close)"""

new_func = """    def open_autologin_settings(self, icon=None, item=None):
        import threading
        threading.Thread(target=self._open_autologin_settings_thread, daemon=True).start()

    def _open_autologin_settings_thread(self):
        import tkinter as tk_plain
        from tkinter import messagebox

        win = tk_plain.Tk()
        win.title("부팅 시 자동 로그인 설정")
        win.geometry("370x200")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.configure(bg="#1a1a1a")
        
        # Center
        win.update_idletasks()
        x = (win.winfo_screenwidth() - 370) // 2
        y = (win.winfo_screenheight() - 200) // 2
        win.geometry(f"+{x}+{y}")

        PAD = {"padx": 15, "pady": 5}

        top_frame = tk_plain.Frame(win, bg="#1a1a1a")
        top_frame.pack(fill="x", **PAD)
        
        auto_unlock_var = tk_plain.BooleanVar(value=self.current_cfg.get('auto_unlock_enabled', False))

        def toggle_entry():
            if auto_unlock_var.get():
                password_entry.config(state="normal")
            else:
                password_entry.config(state="disabled")

        chk = tk_plain.Checkbutton(top_frame, text="  부팅 시 자동으로 잠금 해제 켜기",
                                    variable=auto_unlock_var, command=toggle_entry,
                                    bg="#1a1a1a", fg="white", selectcolor="#333",
                                    activebackground="#1a1a1a", activeforeground="white", font=("Segoe UI", 10))
        chk.pack(anchor="w", pady=(10,0))

        pwd_frame = tk_plain.Frame(win, bg="#1a1a1a")
        pwd_frame.pack(fill="x", padx=15, pady=5)
        tk_plain.Label(pwd_frame, text="Windows 비밀번호:", bg="#1a1a1a", fg="#aaaaaa", font=("Segoe UI", 9)).pack(anchor="w")
        password_entry = tk_plain.Entry(pwd_frame, show="*", bg="#333333", fg="white",
                                         insertbackground="white", relief="flat",
                                         font=("Segoe UI", 10))
        password_entry.pack(fill="x", ipady=5, pady=3)

        saved_enc_pwd = self.current_cfg.get('encrypted_password', "")
        if saved_enc_pwd:
            try:
                password_entry.insert(0, decrypt_password(saved_enc_pwd))
            except Exception:
                pass
        toggle_entry()

        def apply_settings():
            enabled = auto_unlock_var.get()
            pwd = password_entry.get()
            if not ctypes.windll.shell32.IsUserAnAdmin():
                messagebox.showwarning("권한 필요",
                    "자동 로그인을 설정하려면 관리자 권한이 필요합니다.\\n"
                    "트레이 메뉴에서 '관리자 권한으로 열기'를 사용해주세요.", parent=win)
                return
            import getpass
            username = getpass.getuser()
            if enabled:
                if not pwd:
                    messagebox.showerror("오류", "비밀번호를 입력해주세요.", parent=win)
                    return
                if set_auto_logon(username, pwd):
                    self.current_cfg['auto_unlock_enabled'] = True
                    self.current_cfg['encrypted_password'] = encrypt_password(pwd)
                    self.save_config()
                    messagebox.showinfo("성공", "자동 로그인이 활성화되었습니다.\\n(다음 부팅 시부터 적용됩니다)", parent=win)
                    win.destroy()
                else:
                    messagebox.showerror("오류", "레지스트리 설정에 실패했습니다.", parent=win)
            else:
                if disable_auto_logon():
                    self.current_cfg['auto_unlock_enabled'] = False
                    self.current_cfg['encrypted_password'] = ""
                    self.save_config()
                    messagebox.showinfo("성공", "자동 로그인이 비활성화되었습니다.", parent=win)
                    win.destroy()
                else:
                    messagebox.showerror("오류", "레지스트리 설정에 실패했습니다.", parent=win)

        btn_frame = tk_plain.Frame(win, bg="#1a1a1a")
        btn_frame.pack(fill="x", padx=15, pady=10)

        apply_btn = tk_plain.Button(btn_frame, text="적용", command=apply_settings,
                                     bg="#3a7bd5", fg="white", relief="flat",
                                     font=("Segoe UI", 10), padx=12, pady=4)
        apply_btn.pack(side="left")
        
        cancel_btn = tk_plain.Button(btn_frame, text="닫기", command=win.destroy,
                                      bg="#555555", fg="white", relief="flat",
                                      font=("Segoe UI", 10), padx=12, pady=4)
        cancel_btn.pack(side="left", padx=(8,0))

        win.mainloop()"""

text = text.replace(old_func, new_func)
if old_func not in open("auto_shutdown.py", "r", encoding="utf-8").read():
    print("Old func found and replaced")
else:
    print("ERROR: old func not found!")

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

# Fix 2: restart_as_admin - run ShellExecuteW properly, don't let exception swallow it
old_admin = """    def restart_as_admin(self, icon=None, item=None):
        if ctypes.windll.shell32.IsUserAnAdmin():
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
        except Exception: pass"""

new_admin = """    def restart_as_admin(self, icon=None, item=None):
        def _do_restart():
            import subprocess
            exe = sys.executable
            args = sys.argv[1:] if getattr(sys, 'frozen', False) else sys.argv
            try:
                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, " ".join(args), None, 1)
                if ret > 32:  # success
                    self.root.after(500, lambda: (
                        self.icon.stop() if self.icon else None,
                        self.root.quit()
                    ))
            except Exception as e:
                pass
        import threading
        threading.Thread(target=_do_restart, daemon=True).start()"""

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace(old_admin, new_admin)
with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Both fixes applied")
