"""
manual_updater.py - 수동 업데이트 프로그램 (더블클릭 실행)

동작 순서:
  1. Firebase 에서 최신 download_url 조회
  2. 실행 중인 auto_shutdown.exe 프로세스 강제 종료 (이름 기준)
  3. 새 파일 다운로드
  4. %LOCALAPPDATA%\AutoShutdown\auto_shutdown.exe 교체
  5. 새 프로세스 실행
  6. 자기 자신 종료
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

INSTALL_DIR  = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "AutoShutdown")
EXE_NAME     = "auto_shutdown.exe"
FIREBASE_URL = "https://atss-a1f9e-default-rtdb.firebaseio.com/update_info.json"

try:
    _ssl_ctx = ssl._create_unverified_context()
    _ssl_ctx.verify_mode = ssl.CERT_NONE
    _ssl_ctx.check_hostname = False
except Exception:
    _ssl_ctx = None


def _kill_by_name(name: str):
    """프로세스 이름으로 강제 종료"""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass


class ManualUpdaterApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("스마트 전원 관리자 - 수동 업데이트")
        self.root.geometry("420x200")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        tk.Label(
            self.root, text="⬆  수동 업데이트",
            font=("Malgun Gothic", 14, "bold"),
            bg="#1e1e2e", fg="#cba6f7"
        ).pack(pady=(20, 4))

        self.status_var = tk.StringVar(value="업데이트 준비 중...")
        tk.Label(
            self.root, textvariable=self.status_var,
            font=("Malgun Gothic", 9), bg="#1e1e2e", fg="#89b4fa"
        ).pack(pady=(8, 4))

        self.progress = ttk.Progressbar(
            self.root, orient="horizontal", length=360, mode="determinate"
        )
        self.progress.pack()

        self.btn = tk.Button(
            self.root, text="지금 업데이트",
            font=("Malgun Gothic", 11, "bold"),
            bg="#cba6f7", fg="#1e1e2e",
            activebackground="#b4befe",
            relief="flat", padx=20, pady=6,
            command=self._on_update
        )
        self.btn.pack(pady=16)

    def _set(self, msg: str, pct: int = None):
        def _do():
            self.status_var.set(msg)
            if pct is not None:
                self.progress["value"] = pct
        self.root.after(0, _do)

    def _on_update(self):
        self.btn.config(state="disabled")
        threading.Thread(target=self._run_update, daemon=True).start()

    def _run_update(self):
        target_exe = os.path.join(INSTALL_DIR, EXE_NAME)
        tmp_path   = target_exe + f".{int(time.time())}.tmp"

        try:
            # 1. 최신 URL 조회
            self._set("서버에서 최신 버전 확인 중...", 5)
            req = urllib.request.Request(FIREBASE_URL, headers={"User-Agent": "ManualUpdater/1.0"})
            with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            dl_url = data.get("download_url")
            if not dl_url:
                raise RuntimeError("다운로드 URL을 가져오지 못했습니다.")

            # 2. 다운로드
            no_cache = dl_url + ("&" if "?" in dl_url else "?") + f"t={int(time.time())}"
            req2 = urllib.request.Request(no_cache, headers={"User-Agent": "ManualUpdater/1.0"})
            self._set("새 버전 다운로드 중...", 10)

            with urllib.request.urlopen(req2, timeout=300, context=_ssl_ctx) as resp:
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
                        pct = 10 + int((downloaded / total) * 70)
                        self._set(
                            f"다운로드 중... {downloaded // 1024 // 1024} MB / {total // 1024 // 1024} MB",
                            pct
                        )
            file_data = b"".join(chunks)

            if len(file_data) < 1_000_000:
                raise RuntimeError(f"다운로드된 파일이 너무 작습니다 ({len(file_data)} bytes).")

            # 3. 임시 파일 저장
            self._set("파일 저장 중...", 82)
            os.makedirs(INSTALL_DIR, exist_ok=True)
            with open(tmp_path, "wb") as f:
                f.write(file_data)

            # 4. 기존 프로세스 종료
            self._set("기존 프로그램 종료 중...", 88)
            _kill_by_name(EXE_NAME)
            time.sleep(1.5)  # 프로세스가 완전히 죽을 때까지 대기

            # 5. 파일 교체
            self._set("파일 교체 중...", 93)
            if os.path.exists(target_exe):
                os.remove(target_exe)
            os.rename(tmp_path, target_exe)

            # 6. 새 프로세스 실행
            self._set("업데이트 완료! 프로그램 재시작 중...", 100)
            clean_env = os.environ.copy()
            for k in list(clean_env.keys()):
                if any(x in k for x in ("MEIPASS", "_MEI", "PYI", "TCL_", "TK_")):
                    del clean_env[k]
            subprocess.Popen(
                [target_exe],
                env=clean_env,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            time.sleep(1)
            self.root.after(0, self.root.destroy)

        except Exception as e:
            # 임시 파일 정리
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            self._set(f"오류: {e}", 0)
            self.root.after(0, lambda: messagebox.showerror("업데이트 오류", str(e)))
            self.root.after(0, lambda: self.btn.config(state="normal"))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ManualUpdaterApp()
    app.run()
