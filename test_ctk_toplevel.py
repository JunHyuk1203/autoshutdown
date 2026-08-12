import customtkinter as ctk
import tkinter as tk_mod
import time

def test_gui():
    root = ctk.CTk()
    root.withdraw()
    
    # Wait a bit to simulate later tray click
    root.after(1000, lambda: open_toplevel(root))
    
    root.mainloop()

def open_toplevel(root):
    top = tk_mod.Toplevel(root)
    top.title("부팅 시 자동 로그인 설정")
    top.geometry("370x205")
    top.resizable(False, False)
    top.configure(bg="#1a1a1a")
    top.attributes("-topmost", True)

    x = (top.winfo_screenwidth() - 370) // 2
    y = (top.winfo_screenheight() - 205) // 2
    top.geometry(f"370x205+{x}+{y}")

    r1 = tk_mod.Frame(top, bg="#1a1a1a")
    r1.pack(fill="x", padx=15, pady=(15, 5))
    tk_mod.Checkbutton(r1, text="  부팅 시 자동으로 잠금 해제 켜기",
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

    r3 = tk_mod.Frame(top, bg="#1a1a1a")
    r3.pack(fill="x", padx=15, pady=(8, 15))
    tk_mod.Button(r3, text="적용",
                  bg="#3a7bd5", fg="white", relief="flat", cursor="hand2",
                  font=("Segoe UI", 10), padx=16, pady=5).pack(side="left")
    tk_mod.Button(r3, text="닫기", command=top.destroy,
                  bg="#555555", fg="white", relief="flat", cursor="hand2",
                  font=("Segoe UI", 10), padx=16, pady=5).pack(side="left", padx=(8, 0))

    top.lift()
    top.focus_force()
    print("Toplevel opened and formatted properly")
    # we will quit after 2 secs to see if it worked
    root.after(2000, root.quit)

test_gui()
