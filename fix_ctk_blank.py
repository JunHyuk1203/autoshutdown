import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

replacement = """    def _open_autologin_settings_gui(self):
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
                
        top.protocol("WM_DELETE_WINDOW", on_close)
"""

text = text.replace("""    def _open_autologin_settings_gui(self):
        top = ctk.CTkToplevel(self.root)
        top.title("자동 로그인 설정")
        top.geometry("350x220")
        top.resizable(False, False)
        top.attributes("-topmost", True)""", replacement)

# replace cancel_btn command
text = text.replace('cancel_btn = ctk.CTkButton(btn_frame, text="닫기", fg_color="gray", command=top.destroy)',
                    'cancel_btn = ctk.CTkButton(btn_frame, text="닫기", fg_color="gray", command=on_close)')
text = text.replace('top.destroy()', 'on_close()')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated GUI workaround")
