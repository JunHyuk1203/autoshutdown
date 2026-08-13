import os
import sys
import json
import time
import urllib.request
import ssl
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

class UpdaterApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("스마트 전원 관리자 - 수동 업데이트")
        self.root.geometry("400x150")
        self.root.resizable(False, False)
        
        self.label = tk.Label(self.root, text="최신 버전을 확인하는 중...", font=("Malgun Gothic", 11))
        self.label.pack(pady=20)
        
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=10)
        
        self.root.after(100, self.start_update)
        
    def start_update(self):
        threading.Thread(target=self.do_update, daemon=True).start()
        
    def do_update(self):
        try:
            url = "https://atss-a1f9e-default-rtdb.firebaseio.com/update_info.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                ssl_context = ssl._create_unverified_context()
                ssl_context.verify_mode = ssl.CERT_NONE
                ssl_context.check_hostname = False
            except AttributeError:
                ssl_context = None
                
            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                data = json.loads(response.read().decode('utf-8'))
                download_url = data.get("download_url")
                
            if not download_url:
                self.root.after(0, lambda: self.label.config(text="다운로드 URL을 찾을 수 없습니다."))
                return
                
            self.root.after(0, lambda: self.label.config(text="업데이트 파일을 다운로드 중입니다..."))
            
            no_cache_url = download_url + (f"&t={int(time.time())}" if "?" in download_url else f"?t={int(time.time())}")
            req = urllib.request.Request(no_cache_url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, timeout=300, context=ssl_context) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                chunks = []
                while True:
                    chunk = response.read(1024 * 64)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        self.root.after(0, lambda p=percent: self.progress.config(value=p))
                
                exe_data = b"".join(chunks)
                
            if len(exe_data) < 1000000:
                self.root.after(0, lambda: messagebox.showerror("오류", "다운로드된 파일이 너무 작습니다. 네트워크를 확인하세요."))
                self.root.quit()
                return
                
            
            # 대상 경로 설정: %LOCALAPPDATA%\AutoShutdown\auto_shutdown.exe
            appdata_path = os.getenv("LOCALAPPDATA")
            app_dir = os.path.join(appdata_path, "AutoShutdown")
            os.makedirs(app_dir, exist_ok=True)
            
            target_exe = os.path.join(app_dir, "auto_shutdown.exe")
            update_temp_path = os.path.join(app_dir, "update_temp.exe")
            
            with open(update_temp_path, "wb") as f:
                f.write(exe_data)
                
            self.root.after(0, lambda: self.label.config(text="업데이트 적용 중..."))
            time.sleep(1)
            
            # 교체 스크립트 실행 (app_dir에 배치 파일 생성)
            bat_path = os.path.join(app_dir, "apply_update.bat")
            bat_script = f"""@echo off
timeout /t 2 /nobreak >nul
taskkill /F /IM auto_shutdown.exe >nul 2>&1
move /Y "{update_temp_path}" "{target_exe}"
start "" "{target_exe}"
del "%~f0"
"""
            with open(bat_path, "w", encoding="euc-kr") as f:
                f.write(bat_script)
                
            subprocess.Popen(f'"{bat_path}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW, cwd=app_dir)
            self.root.after(0, self.root.quit)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("업데이트 오류", f"오류가 발생했습니다:\n{str(e)}"))
            self.root.quit()

if __name__ == "__main__":
    app = UpdaterApp()
    app.root.mainloop()
