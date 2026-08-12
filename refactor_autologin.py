with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

def find_block(start_str, next_str):
    start = -1
    end = -1
    for i, line in enumerate(lines):
        if start_str in line and start == -1:
            start = i
        if start != -1 and i > start and line.startswith(next_str):
            end = i
            break
    return start, end

# 1. Replace the methods in the class
s1, e1 = find_block("    def open_autologin_settings(", "    def get_menu(")
new_methods = """    def open_autologin_settings(self, icon=None, item=None):
        import subprocess
        import sys
        if getattr(sys, 'frozen', False):
            subprocess.Popen([sys.executable, "--autologin-gui"])
        else:
            subprocess.Popen([sys.executable, sys.argv[0], "--autologin-gui"])

"""
lines = lines[:s1] + [new_methods] + lines[e1:]

# 2. Add run_standalone_autologin_gui at the top level
run_gui_func = """
def run_standalone_autologin_gui():
    import tkinter as tk
    from tkinter import messagebox
    import json
    import ctypes
    import getpass
    import os
    import sys

    config_file = 'config.json'
    if getattr(sys, 'frozen', False):
        config_file = os.path.join(os.path.dirname(sys.executable), 'config.json')
    
    current_cfg = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                current_cfg = json.load(f)
        except:
            pass

    def save_cfg():
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(current_cfg, f, ensure_ascii=False, indent=4)
        except:
            pass

    root = tk.Tk()
    root.title("부팅 시 자동 로그인 설정")
    root.geometry("370x205")
    root.resizable(False, False)
    root.configure(bg="#1a1a1a")
    root.attributes("-topmost", True)

    x = (root.winfo_screenwidth() - 370) // 2
    y = (root.winfo_screenheight() - 205) // 2
    root.geometry(f"370x205+{x}+{y}")

    auto_unlock_var = tk.BooleanVar(value=current_cfg.get('auto_unlock_enabled', False))

    def toggle_entry():
        password_entry.config(state="normal" if auto_unlock_var.get() else "disabled")

    r1 = tk.Frame(root, bg="#1a1a1a")
    r1.pack(fill="x", padx=15, pady=(15, 5))
    tk.Checkbutton(r1, text="  부팅 시 자동으로 잠금 해제 켜기",
                       variable=auto_unlock_var, command=toggle_entry,
                       bg="#1a1a1a", fg="white", selectcolor="#555",
                       activebackground="#1a1a1a", activeforeground="white",
                       font=("Segoe UI", 10)).pack(anchor="w")

    r2 = tk.Frame(root, bg="#1a1a1a")
    r2.pack(fill="x", padx=15, pady=4)
    tk.Label(r2, text="Windows 비밀번호:", font=("Segoe UI", 9),
                 bg="#1a1a1a", fg="#aaaaaa").pack(anchor="w")
    
    pwd_frame = tk.Frame(root, bg="#1a1a1a")
    pwd_frame.pack(fill="x", padx=15, pady=(0, 10))
    password_entry = tk.Entry(pwd_frame, show="*", font=("Segoe UI", 10),
                                  bg="#333333", fg="white", insertbackground="white",
                                  relief="flat", disabledbackground="#222222")
    password_entry.pack(fill="x", ipady=6, pady=(2, 0))

    saved_enc_pwd = current_cfg.get('encrypted_password', "")
    if saved_enc_pwd:
        try:
            password_entry.insert(0, decrypt_password(saved_enc_pwd))
        except:
            pass
    toggle_entry()

    def apply_settings():
        enabled = auto_unlock_var.get()
        pwd = password_entry.get()
        if not ctypes.windll.shell32.IsUserAnAdmin():
            messagebox.showwarning("권한 필요",
                "관리자 권한이 필요합니다.\\n트레이 메뉴에서 '관리자 권한으로 열기'를 먼저 사용해주세요.")
            return
        
        username = getpass.getuser()
        if enabled:
            if not pwd:
                messagebox.showerror("오류", "비밀번호를 입력해주세요.")
                return
            if set_auto_logon(username, pwd):
                current_cfg['auto_unlock_enabled'] = True
                current_cfg['encrypted_password'] = encrypt_password(pwd)
                save_cfg()
                messagebox.showinfo("성공", "자동 로그인이 활성화되었습니다.\\n(다음 부팅 시부터 적용됩니다)")
                root.destroy()
            else:
                messagebox.showerror("오류", "레지스트리 설정에 실패했습니다.")
        else:
            if disable_auto_logon():
                current_cfg['auto_unlock_enabled'] = False
                current_cfg['encrypted_password'] = ""
                save_cfg()
                messagebox.showinfo("성공", "자동 로그인이 비활성화되었습니다.")
                root.destroy()
            else:
                messagebox.showerror("오류", "레지스트리 설정에 실패했습니다.")

    r3 = tk.Frame(root, bg="#1a1a1a")
    r3.pack(fill="x", padx=15, pady=(8, 15))
    tk.Button(r3, text="적용", command=apply_settings,
                  bg="#3a7bd5", fg="white", relief="flat", cursor="hand2",
                  font=("Segoe UI", 10), padx=16, pady=5).pack(side="left")
    tk.Button(r3, text="닫기", command=root.destroy,
                  bg="#555555", fg="white", relief="flat", cursor="hand2",
                  font=("Segoe UI", 10), padx=16, pady=5).pack(side="left", padx=(8, 0))

    root.mainloop()

"""
# Find import section end
s2 = 0
for i, line in enumerate(lines):
    if line.startswith("CURRENT_VERSION"):
        s2 = i
        break
lines = lines[:s2] + [run_gui_func] + lines[s2:]

# 3. Add interception in if __name__ == '__main__':
s3 = 0
for i, line in enumerate(lines):
    if "if __name__ == \"__main__\":" in line:
        s3 = i + 1
        break

injection = """    import sys
    if "--autologin-gui" in sys.argv:
        run_standalone_autologin_gui()
        sys.exit(0)

"""
lines = lines[:s3] + [injection] + lines[s3:]

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Replacement successful")
