"""
installer.py - 스마트 전원 관리자 설치 프로그램
파이썬 없는 컴퓨터에서도 동작하는 단독 설치파일 (PyInstaller --onefile 빌드)

동작 순서:
  1. Firebase 에서 최신 버전 download_url 조회
  2. %LOCALAPPDATA%\AutoShutdown\ 폴더 생성
  3. auto_shutdown.exe 다운로드
  4. 바탕화면 바로가기 생성
  5. (선택) 시작프로그램 등록
  6. 설치 완료 후 프로그램 실행
"""

import sys
import os
import time
import json
import threading
import urllib.request
import ssl
import subprocess
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox

# ─── 설치 경로 ─────────────────────────────────────────────────────────────────
INSTALL_DIR  = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "AutoShutdown")
EXE_NAME     = "auto_shutdown.exe"
APP_NAME     = "스마트 전원 관리자"
FIREBASE_URL = "https://atss-a1f9e-default-rtdb.firebaseio.com/update_info.json"

# ─── SSL 컨텍스트 ───────────────────────────────────────────────────────────────
try:
    _ssl_ctx = ssl._create_unverified_context()
    _ssl_ctx.verify_mode = ssl.CERT_NONE
    _ssl_ctx.check_hostname = False
except Exception:
    _ssl_ctx = None


def _fetch_download_url():
    req = urllib.request.Request(FIREBASE_URL, headers={"User-Agent": "SmartPower-Installer/1.0"})
    with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    url = data.get("download_url")
    if not url:
        raise RuntimeError("다운로드 URL을 가져오지 못했습니다.")
    return url


def _create_shortcut(target_path: str, shortcut_path: str, description: str = ""):
    """WScript.Shell 을 이용한 .lnk 바로가기 생성"""
    import winreg  # noqa – only runs on Windows
    try:
        shell = ctypes.windll.shell32
    except Exception:
        pass

    vbs = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{shortcut_path}")
oLink.TargetPath = "{target_path}"
oLink.WorkingDirectory = "{os.path.dirname(target_path)}"
oLink.Description = "{description}"
oLink.Save
"""
    vbs_path = os.path.join(os.environ.get("TEMP", INSTALL_DIR), "_create_shortcut.vbs")
    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write(vbs)
    subprocess.run(["wscript.exe", vbs_path], check=True,
                   creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        os.remove(vbs_path)
    except Exception:
        pass


def _add_startup_registry(name: str, exe_path: str):
    """HKCU 시작프로그램 레지스트리 등록"""
    import winreg
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE
    )
    winreg.SetValueEx(key, name, 0, winreg.REG_SZ, f'"{exe_path}" --headless')
    winreg.CloseKey(key)


# ─── GUI ───────────────────────────────────────────────────────────────────────
class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} 설치")
        self.root.geometry("460x280")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        # 타이틀
        tk.Label(
            self.root, text=f"⚡ {APP_NAME}", font=("Malgun Gothic", 16, "bold"),
            bg="#1e1e2e", fg="#cba6f7"
        ).pack(pady=(24, 4))
        tk.Label(
            self.root, text="자동 종료 / 원격 제어 관리 도구", font=("Malgun Gothic", 10),
            bg="#1e1e2e", fg="#a6adc8"
        ).pack()

        # 구분선
        tk.Frame(self.root, height=1, bg="#313244").pack(fill="x", padx=24, pady=12)

        # 체크박스
        self.var_desktop  = tk.BooleanVar(value=True)
        self.var_startup  = tk.BooleanVar(value=True)
        opt_frame = tk.Frame(self.root, bg="#1e1e2e")
        opt_frame.pack(padx=32, fill="x")
        tk.Checkbutton(
            opt_frame, text="바탕화면 바로가기 만들기",
            variable=self.var_desktop, bg="#1e1e2e", fg="#cdd6f4",
            selectcolor="#313244", activebackground="#1e1e2e",
            font=("Malgun Gothic", 10)
        ).pack(anchor="w")
        tk.Checkbutton(
            opt_frame, text="Windows 시작 시 자동 실행 (백그라운드)",
            variable=self.var_startup, bg="#1e1e2e", fg="#cdd6f4",
            selectcolor="#313244", activebackground="#1e1e2e",
            font=("Malgun Gothic", 10)
        ).pack(anchor="w", pady=(4, 0))

        # 설치 경로 표시
        tk.Label(
            self.root, text=f"설치 경로:  {INSTALL_DIR}",
            font=("Malgun Gothic", 8), bg="#1e1e2e", fg="#6c7086"
        ).pack(pady=(10, 0))

        # 진행바 & 상태 라벨
        self.status_var = tk.StringVar(value="설치 준비 중...")
        tk.Label(
            self.root, textvariable=self.status_var,
            font=("Malgun Gothic", 9), bg="#1e1e2e", fg="#89b4fa"
        ).pack(pady=(10, 4))

        self.progress = ttk.Progressbar(
            self.root, orient="horizontal", length=400, mode="determinate"
        )
        self.progress.pack()

        # 설치 버튼
        self.btn = tk.Button(
            self.root, text="설  치  하  기",
            font=("Malgun Gothic", 11, "bold"),
            bg="#cba6f7", fg="#1e1e2e",
            activebackground="#b4befe",
            relief="flat", padx=20, pady=6,
            command=self._on_install
        )
        self.btn.pack(pady=14)

    def _set_status(self, msg: str, pct: int = None):
        def _do():
            self.status_var.set(msg)
            if pct is not None:
                self.progress["value"] = pct
        self.root.after(0, _do)

    def _on_install(self):
        self.btn.config(state="disabled")
        self._set_status("서버에서 최신 버전 확인 중...", 0)
        threading.Thread(target=self._install, daemon=True).start()

    def _install(self):
        do_desktop = self.var_desktop.get()
        do_startup = self.var_startup.get()

        try:
            # 1. 다운로드 URL 조회
            self._set_status("최신 버전 URL 조회 중...", 5)
            dl_url = _fetch_download_url()

            # 2. 설치 폴더 생성
            self._set_status("설치 폴더 생성 중...", 10)
            os.makedirs(INSTALL_DIR, exist_ok=True)
            target_exe = os.path.join(INSTALL_DIR, EXE_NAME)

            # 3. 다운로드
            no_cache = dl_url + ("&" if "?" in dl_url else "?") + f"t={int(time.time())}"
            req = urllib.request.Request(no_cache, headers={"User-Agent": "SmartPower-Installer/1.0"})
            self._set_status("프로그램 파일 다운로드 중...", 15)

            with urllib.request.urlopen(req, timeout=300, context=_ssl_ctx) as resp:
                total = int(resp.info().get("Content-Length", 0))
                downloaded = 0
                chunks = []
                while True:
                    chunk = resp.read(1024 * 64)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = 15 + int((downloaded / total) * 70)
                        self._set_status(
                            f"다운로드 중... ({downloaded // 1024 // 1024} MB / {total // 1024 // 1024} MB)",
                            pct
                        )
                data = b"".join(chunks)

            if len(data) < 1_000_000:
                raise RuntimeError(f"다운로드된 파일이 너무 작습니다 ({len(data)} bytes). 네트워크를 확인하세요.")

            # 4. 파일 저장
            self._set_status("파일 설치 중...", 86)
            tmp_path = target_exe + ".tmp"
            with open(tmp_path, "wb") as f:
                f.write(data)
            if os.path.exists(target_exe):
                os.remove(target_exe)
            os.rename(tmp_path, target_exe)

            # 5. 바탕화면 바로가기
            if do_desktop:
                self._set_status("바탕화면 바로가기 생성 중...", 90)
                try:
                    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                    lnk_path = os.path.join(desktop, f"{APP_NAME}.lnk")
                    _create_shortcut(target_exe, lnk_path, APP_NAME)
                except Exception as e:
                    pass  # 바로가기 실패는 무시

            # 6. 시작프로그램 등록
            if do_startup:
                self._set_status("시작프로그램 등록 중...", 94)
                try:
                    _add_startup_registry(APP_NAME, target_exe)
                except Exception:
                    pass

            # 7. 완료 & 실행
            self._set_status("설치 완료! 프로그램을 시작합니다...", 100)
            time.sleep(1)

            clean_env = os.environ.copy()
            for k in list(clean_env.keys()):
                if any(x in k for x in ("MEIPASS", "_MEI", "PYI", "TCL_", "TK_")):
                    del clean_env[k]
            subprocess.Popen(
                [target_exe],
                env=clean_env,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )

            self.root.after(0, lambda: messagebox.showinfo(
                "설치 완료",
                f"{APP_NAME}이(가) 성공적으로 설치되었습니다!\n\n"
                f"설치 경로:\n{INSTALL_DIR}\n\n"
                f"프로그램이 시작됩니다."
            ))
            self.root.after(0, self.root.destroy)

        except Exception as e:
            self._set_status(f"오류 발생: {e}", 0)
            self.root.after(0, lambda: messagebox.showerror(
                "설치 오류",
                f"설치 중 오류가 발생했습니다:\n\n{e}"
            ))
            self.root.after(0, lambda: self.btn.config(state="normal"))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = InstallerApp()
    app.run()
