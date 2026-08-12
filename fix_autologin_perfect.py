with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if "    def _open_autologin_settings_gui(self):" in line:
        start_idx = i
    if start_idx != -1 and i > start_idx and line.startswith("    def "):
        end_idx = i
        break

new_func = """    def _open_autologin_settings_gui(self):
        import tkinter as tk_mod
        from tkinter import messagebox

        top = tk_mod.Toplevel(self.root)
        top.title("부팅 시 자동 로그인 설정")
        top.geometry("370x205")
        top.resizable(False, False)
        top.configure(bg="#1a1a1a")
        top.attributes("-topmost", True)

        # Center explicitly using fixed dimensions
        x = (top.winfo_screenwidth() - 370) // 2
        y = (top.winfo_screenheight() - 205) // 2
        top.geometry(f"370x205+{x}+{y}")

        def on_close():
            top.destroy()

        top.protocol("WM_DELETE_WINDOW", on_close)

        auto_unlock_var = tk_mod.BooleanVar(value=self.current_cfg.get('auto_unlock_enabled', False))

        def toggle_entry():
            password_entry.config(state="normal" if auto_unlock_var.get() else "disabled")

        r1 = tk_mod.Frame(top, bg="#1a1a1a")
        r1.pack(fill="x", padx=15, pady=(15, 5))
        tk_mod.Checkbutton(r1, text="  부팅 시 자동으로 잠금 해제 켜기",
                           variable=auto_unlock_var, command=toggle_entry,
                           bg="#1a1a1a", fg="white", selectcolor="#555",
                           activebackground="#1a1a1a", activeforeground="white",
                           font=("Segoe UI", 10)).pack(anchor="w")

        r2 = tk_mod.Frame(top, bg="#1a1a1a")
        r2.pack(fill="x", padx=15, pady=4)
        tk_mod.Label(r2, text="Windows 비밀번호:", font=("Segoe UI", 9),
                     bg="#1a1a1a", fg="#aaaaaa").pack(anchor="w")
        
        pwd_frame = tk_mod.Frame(top, bg="#1a1a1a")
        pwd_frame.pack(fill="x", padx=15, pady=(0, 10))
        password_entry = tk_mod.Entry(pwd_frame, show="*", font=("Segoe UI", 10),
                                      bg="#333333", fg="white", insertbackground="white",
                                      relief="flat", disabledbackground="#222222")
        password_entry.pack(fill="x", ipady=6, pady=(2, 0))

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

        r3 = tk_mod.Frame(top, bg="#1a1a1a")
        r3.pack(fill="x", padx=15, pady=(8, 15))
        tk_mod.Button(r3, text="적용", command=apply_settings,
                      bg="#3a7bd5", fg="white", relief="flat", cursor="hand2",
                      font=("Segoe UI", 10), padx=16, pady=5).pack(side="left")
        tk_mod.Button(r3, text="닫기", command=on_close,
                      bg="#555555", fg="white", relief="flat", cursor="hand2",
                      font=("Segoe UI", 10), padx=16, pady=5).pack(side="left", padx=(8, 0))

        top.lift()
        top.focus_force()

"""
new_lines = lines[:start_idx] + [new_func] + lines[end_idx:]
with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print(f"Done, replaced lines {start_idx+1} to {end_idx}")
