import tkinter as tk
import time

def test_gui():
    root = tk.Tk()
    
    # Hide root properly
    root.withdraw()
    
    # Wait a bit to simulate later tray click
    root.after(1000, lambda: open_toplevel(root))
    
    root.mainloop()

def open_toplevel(root):
    top = tk.Toplevel(root)
    top.title("Test Settings")
    top.geometry("370x205")
    top.resizable(False, False)
    
    # Let's see what happens if we just pack widgets
    chk_frame = tk.Frame(top)
    chk_frame.pack(fill="x", padx=15, pady=(15, 5))
    tk.Checkbutton(chk_frame, text="부팅 시 자동으로 잠금 해제 켜기").pack(anchor="w")

    lbl_frame = tk.Frame(top)
    lbl_frame.pack(fill="x", padx=15, pady=(8, 2))
    tk.Label(lbl_frame, text="Windows 비밀번호:").pack(anchor="w")

    pwd_frame = tk.Frame(top)
    pwd_frame.pack(fill="x", padx=15, pady=(0, 10))
    tk.Entry(pwd_frame, show="*").pack(fill="x", ipady=6)

    btn_frame = tk.Frame(top)
    btn_frame.pack(fill="x", padx=15, pady=(0, 15))
    tk.Button(btn_frame, text="적용").pack(side="left")
    tk.Button(btn_frame, text="닫기", command=top.destroy).pack(side="left", padx=(8, 0))

    # Center WITHOUT reqwidth/reqheight which might be bugged
    top.update_idletasks()
    # x = (top.winfo_screenwidth() - 370) // 2
    # y = (top.winfo_screenheight() - 205) // 2
    # top.geometry(f"+{x}+{y}")
    
    top.lift()
    top.focus_force()
    print("Toplevel opened")
    # we will quit after 2 secs to see if it worked
    root.after(2000, root.quit)

test_gui()
