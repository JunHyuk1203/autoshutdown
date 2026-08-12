import re
with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

# Find and replace the entire open_autologin_settings block
start_marker = "    def open_autologin_settings(self, icon=None, item=None):"
end_marker = "    def get_menu(self):"

idx_start = text.find(start_marker)
idx_end = text.find(end_marker)

if idx_start == -1 or idx_end == -1:
    print("ERROR: markers not found")
    exit(1)

new_func = """    def open_autologin_settings(self, icon=None, item=None):
        # pystray calls this from its own thread - must schedule on main tk thread
        self.root.after(0, self._open_autologin_settings_gui)

    def _open_autologin_settings_gui(self):
        import tkinter as tk_mod
        from tkinter import messagebox

        # Temporarily show root (alpha=0) so Toplevel renders correctly
        was_withdrawn = not self.root.winfo_viewable()
        if was_withdrawn:
            self.root.attributes('-alpha', 0.0)
            self.root.deiconify()

        top = tk_mod.Toplevel(self.root)
        top.title("부팅 시 자동 로그인 설정")
        top.geometry("370x205")
        top.resizable(False, False)
        top.configure(bg="#1a1a1a")
        top.attributes("-topmost", True)
        top.update()  # force render before anything

        # Center
        x = (top.winfo_screenwidth() - 370) // 2
        y = (top.winfo_screenheight() - 205) // 2
        top.geometry(f"+{x}+{y}")

        def on_close():
            top.destroy()
            if was_withdrawn:
                self.root.withdraw()
                self.root.attributes('-alpha', 1.0)

        top.protocol("WM_DELETE_WINDOW", on_close)

        # --- Widgets ---
        pad = dict(padx=15, pady=4)

        auto_unlock_var = tk_mod.BooleanVar(top, value=self.current_cfg.get('auto_unlock_enabled', False))

        def toggle_entry():
            state = "normal" if auto_unlock_var.get() else "disabled"
            password_entry.config(state=state)

        chk_frame = tk_mod.Frame(top, bg="#1a1a1a")
        chk_frame.pack(fill="x", padx=15, pady=(15, 5))
        chk = tk_mod.Checkbutton(chk_frame, text="  부팅 시 자동으로 잠금 해제 켜기",
                                   variable=auto_unlock_var, command=toggle_entry,
                                   bg="#1a1a1a", fg="white", selectcolor="#555",
                                   activebackground="#1a1a1a", activeforeground="white",
                                   font=("Segoe UI", 10))
        chk.pack(anchor="w")

        lbl_frame = tk_mod.Frame(top, bg="#1a1a1a")
        lbl_frame.pack(fill="x", padx=15, pady=(8, 2))
        tk_mod.Label(lbl_frame, text="Windows 비밀번호:", bg="#1a1a1a",
                     fg="#aaaaaa", font=("Segoe UI", 9)).pack(anchor="w")

        pwd_frame = tk_mod.Frame(top, bg="#1a1a1a")
        pwd_frame.pack(fill="x", padx=15, pady=(0, 10))
        password_entry = tk_mod.Entry(pwd_frame, show="*", bg="#333333", fg="white",
                                       insertbackground="white", relief="flat",
                                       disabledbackground="#222222",
                                       font=("Segoe UI", 10))
        password_entry.pack(fill="x", ipady=6)

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
                    "관리자 권한이 필요합니다.\\n트레이 메뉴에서 '관리자 권한으로 열기'를 먼저 사용해주세요.",
                    parent=top)
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
                    on_close()
                else:
                    messagebox.showerror("오류", "레지스트리 설정에 실패했습니다.", parent=top)
            else:
                if disable_auto_logon():
                    self.current_cfg['auto_unlock_enabled'] = False
                    self.current_cfg['encrypted_password'] = ""
                    self.save_config()
                    messagebox.showinfo("성공", "자동 로그인이 비활성화되었습니다.", parent=top)
                    on_close()
                else:
                    messagebox.showerror("오류", "레지스트리 설정에 실패했습니다.", parent=top)

        btn_frame = tk_mod.Frame(top, bg="#1a1a1a")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        apply_btn = tk_mod.Button(btn_frame, text="적용", command=apply_settings,
                                    bg="#3a7bd5", fg="white", relief="flat",
                                    font=("Segoe UI", 10), padx=16, pady=5,
                                    cursor="hand2")
        apply_btn.pack(side="left")

        cancel_btn = tk_mod.Button(btn_frame, text="닫기", command=on_close,
                                     bg="#555555", fg="white", relief="flat",
                                     font=("Segoe UI", 10), padx=16, pady=5,
                                     cursor="hand2")
        cancel_btn.pack(side="left", padx=(8, 0))

        top.lift()
        top.focus_force()

    """

text = text[:idx_start] + new_func + text[idx_end:]
with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Done - replaced autologin settings GUI")
