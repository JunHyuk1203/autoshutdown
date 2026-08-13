"""
updater.exe - 독립 업데이트 프로세스
사용법: updater.exe <pid> <download_url> <target_exe_path> [extra_args...]

동작 순서:
  1. <pid> 프로세스가 종료될 때까지 대기 (5초 후 강제 종료)
  2. <download_url> 에서 새 exe 다운로드
  3. <target_exe_path> 를 새 파일로 교체
  4. <target_exe_path> [extra_args] 로 새 프로세스 실행
  5. 자기 자신 종료
"""
import sys
import os
import time
import urllib.request
import ssl
import subprocess
import ctypes


def _wait_for_pid(pid: int, timeout_sec: int = 5) -> bool:
    """프로세스가 종료될 때까지 대기. 종료되면 True 반환."""
    SYNCHRONIZE = 0x00100000
    PROCESS_QUERY_LIMITED = 0x1000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED, False, pid)
    if not handle:
        return True  # 이미 없음
    result = kernel32.WaitForSingleObject(handle, timeout_sec * 1000)
    kernel32.CloseHandle(handle)
    return result == 0  # WAIT_OBJECT_0 = 정상 종료


def _kill_pid(pid: int):
    """프로세스를 강제 종료."""
    PROCESS_TERMINATE = 0x0001
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if handle:
        kernel32.TerminateProcess(handle, 1)
        kernel32.CloseHandle(handle)


def main():
    if len(sys.argv) < 4:
        sys.exit(1)

    pid        = int(sys.argv[1])
    dl_url     = sys.argv[2]
    target_exe = sys.argv[3]
    extra_args = sys.argv[4:]  # 예: ["--headless"]

    log_dir  = os.path.dirname(target_exe)
    log_path = os.path.join(log_dir, "updater.log")

    def log(msg):
        try:
            os.makedirs(log_dir, exist_ok=True)
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        except Exception:
            pass

    log(f"=== Updater started === pid={pid} url={dl_url} target={target_exe}")

    # 1. 메인 프로세스 종료 대기
    log("Waiting for main process to exit (5s)...")
    if not _wait_for_pid(pid, timeout_sec=5):
        log("Process still alive after 5s — force killing.")
        _kill_pid(pid)
        time.sleep(1)
    log("Main process is gone.")

    # 2. 다운로드
    tmp_path = target_exe + f".{int(time.time())}.tmp"
    no_cache = dl_url + ("&" if "?" in dl_url else "?") + f"t={int(time.time())}"
    log(f"Downloading: {no_cache}")

    try:
        ctx = ssl._create_unverified_context()
        ctx.verify_mode = ssl.CERT_NONE
        ctx.check_hostname = False
    except Exception:
        ctx = None

    try:
        req = urllib.request.Request(no_cache, headers={"User-Agent": "AutoShutdown-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=300, context=ctx) as resp:
            data = resp.read()
        log(f"Download complete. Size={len(data)} bytes")
    except Exception as e:
        log(f"Download FAILED: {e}")
        sys.exit(1)

    if len(data) < 1_000_000:
        log(f"File too small ({len(data)} bytes). Aborting.")
        sys.exit(1)

    # 3. 임시 파일로 저장
    try:
        os.makedirs(os.path.dirname(target_exe), exist_ok=True)
        with open(tmp_path, 'wb') as f:
            f.write(data)
        log(f"Saved to tmp: {tmp_path}")
    except Exception as e:
        log(f"Save FAILED: {e}")
        sys.exit(1)

    # 4. 기존 파일 삭제 후 교체
    try:
        if os.path.exists(target_exe):
            os.remove(target_exe)
        os.rename(tmp_path, target_exe)
        log(f"Replaced: {target_exe}")
    except Exception as e:
        log(f"Replace FAILED: {e}")
        # 임시 파일 정리
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        sys.exit(1)

    # 5. 새 프로세스 실행
    try:
        clean_env = os.environ.copy()
        for k in list(clean_env.keys()):
            if any(x in k for x in ("MEIPASS", "_MEI", "PYI", "TCL_", "TK_")):
                del clean_env[k]

        cmd = [target_exe] + extra_args
        subprocess.Popen(
            cmd,
            env=clean_env,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        log(f"Launched: {cmd}")
    except Exception as e:
        log(f"Launch FAILED: {e}")

    log("=== Updater done. Exiting. ===")
    sys.exit(0)


if __name__ == "__main__":
    main()
