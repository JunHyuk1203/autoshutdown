import os
import sys
import shutil
import time
import subprocess
import threading
import ctypes
import customtkinter as ctk
from tkinter import messagebox

# Set theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class Installer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("스마트 전원 관리자 설치")
        self.geometry("400x250")
        self.resizable(False, False)
        
        # Center window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # UI Elements
        self.title_lbl = ctk.CTkLabel(self, text="스마트 전원 관리자 설치", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_lbl.pack(pady=(20, 10))
        
        self.info_lbl = ctk.CTkLabel(self, text="USB 배포용 설치 프로그램입니다.\n설치를 클릭하면 내 PC에 프로그램이 복사됩니다.", font=ctk.CTkFont(size=12))
        self.info_lbl.pack(pady=10)
        
        self.progress = ctk.CTkProgressBar(self, width=300)
        self.progress.pack(pady=15)
        self.progress.set(0)
        
        self.status_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11), text_color="gray")
        self.status_lbl.pack(pady=(0, 5))
        
        self.btn_install = ctk.CTkButton(self, text="설치 시작", command=self.start_install)
        self.btn_install.pack(pady=5)
        
    def create_shortcut(self, target, shortcut_path):
        script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target}"
oLink.WindowStyle = 1
oLink.Save
'''
        vbs_path = os.path.join(os.environ['TEMP'], "create_shortcut.vbs")
        with open(vbs_path, "w", encoding="euc-kr") as f:
            f.write(script)
        subprocess.run(["cscript.exe", "//Nologo", vbs_path], creationflags=subprocess.CREATE_NO_WINDOW)
        try: os.remove(vbs_path)
        except: pass

    def start_install(self):
        self.btn_install.configure(state="disabled")
        threading.Thread(target=self.install_process, daemon=True).start()
        
    def install_process(self):
        try:
            self.status_lbl.configure(text="기존 프로세스 종료 중...")
            self.progress.set(0.1)
            subprocess.run(["taskkill", "/f", "/im", "auto_shutdown.exe"], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(1)
            
            self.status_lbl.configure(text="파일 복사 준비 중...")
            self.progress.set(0.3)
            
            install_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'AutoShutdown')
            if not os.path.exists(install_dir):
                os.makedirs(install_dir)
                
            if getattr(sys, 'frozen', False):
                source_exe = os.path.join(sys._MEIPASS, 'auto_shutdown.exe')
            else:
                source_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist', 'auto_shutdown.exe')
                
            if not os.path.exists(source_exe):
                self.status_lbl.configure(text="오류: 원본 파일을 찾을 수 없습니다.")
                messagebox.showerror("오류", "설치 패키지가 손상되었습니다.\n원본 실행 파일을 찾을 수 없습니다.")
                self.btn_install.configure(state="normal")
                return
                
            target_exe = os.path.join(install_dir, 'auto_shutdown.exe')
            
            self.status_lbl.configure(text="프로그램 파일 복사 중...")
            self.progress.set(0.6)
            shutil.copy2(source_exe, target_exe)
            
            self.status_lbl.configure(text="바로가기 생성 중...")
            self.progress.set(0.8)
            
            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
            shortcut_path = os.path.join(desktop, '스마트 전원 관리자.lnk')
            self.create_shortcut(target_exe, shortcut_path)
            
            start_menu = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs')
            if not os.path.exists(start_menu):
                os.makedirs(start_menu)
            shortcut_path = os.path.join(start_menu, '스마트 전원 관리자.lnk')
            self.create_shortcut(target_exe, shortcut_path)
            
            self.status_lbl.configure(text="설치 완료 및 프로그램 실행 중...")
            self.progress.set(1.0)
            
            subprocess.Popen([target_exe], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
            
            messagebox.showinfo("설치 완료", "스마트 전원 관리자가 성공적으로 설치되었습니다!\n바탕화면의 바로가기를 확인해주세요.")
            self.quit()
        except Exception as e:
            self.status_lbl.configure(text="설치 실패")
            messagebox.showerror("설치 오류", f"설치 중 오류가 발생했습니다:\n{e}")
            self.btn_install.configure(state="normal")

if __name__ == "__main__":
    app = Installer()
    app.mainloop()
