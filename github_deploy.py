import os
import re
import json
import subprocess
import time
import sys
import urllib.request
import ssl

# Windows CMD 인코딩 강제 설정
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# exe로 실행될 때와 .py로 실행될 때 모두 올바른 기준 경로 사용
if getattr(sys, 'frozen', False):
    # PyInstaller exe 실행 시 → exe 파일이 있는 폴더를 기준으로
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("==================================================")
print("[AutoShutdown] 배포 자동화 프로그램 시작")
print(f"기준 경로: {BASE_DIR}")
print("==================================================")

app_path = os.path.join(BASE_DIR, "auto_shutdown.py")
spec_path = os.path.join(BASE_DIR, "auto_shutdown.spec")
version_path = os.path.join(BASE_DIR, "version.json")
git_exe = r"C:\Program Files\Git\cmd\git.exe"

if not os.path.exists(app_path):
    print(f"[Error] {app_path} 파일을 찾을 수 없습니다.")
    print("배포 프로그램은 auto_shutdown.py 파일과 같은 폴더에 있어야 합니다.")
    time.sleep(5)
    exit(1)

if not os.path.exists(spec_path):
    print(f"[Error] {spec_path} 파일을 찾을 수 없습니다.")
    time.sleep(5)
    exit(1)

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

version_match = re.search(r'CURRENT_VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
if not version_match:
    print("[Error] 버전 정보(CURRENT_VERSION)를 찾을 수 없습니다.")
    time.sleep(5)
    exit(1)

major, minor, patch = int(version_match.group(1)), int(version_match.group(2)), int(version_match.group(3))
current_v = f"{major}.{minor}.{patch}"
new_v = f"{major}.{minor}.{patch+1}"

print(f"\n[1단계] 버전 업그레이드 ({current_v} -> {new_v})")
content = content.replace(f'CURRENT_VERSION = "{current_v}"', f'CURRENT_VERSION = "{new_v}"')
with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n[2단계] 기존 실행 중인 프로그램 강제 종료 중...")
try:
    subprocess.run(["taskkill", "/F", "/IM", "auto_shutdown.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except:
    pass
time.sleep(1)

print("\n[3단계] PyInstaller 빌드 중... (시간이 걸릴 수 있습니다)")
try:
    subprocess.run(
        ["pyinstaller", "--clean", "--noconfirm", spec_path],
        check=True,
        cwd=BASE_DIR
    )
except Exception as e:
    print(f"[Error] 빌드 실패: {e}")
    # 원상 복구
    content = content.replace(f'CURRENT_VERSION = "{new_v}"', f'CURRENT_VERSION = "{current_v}"')
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(content)
    time.sleep(5)
    exit(1)

print("\n[4단계] version.json 업데이트 및 Firebase 업로드 중...")
version_data = {
    "version": new_v,
    "download_url": "https://cdn.jsdelivr.net/gh/JunHyuk1203/autoshutdown@main/dist/auto_shutdown.exe"
}
with open(version_path, "w", encoding="utf-8") as f:
    json.dump(version_data, f, indent=4)

# Firebase RTDB에 업데이트 정보 업로드
firebase_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/update_info.json"
version_payload = json.dumps(version_data).encode('utf-8')
req = urllib.request.Request(
    firebase_url,
    data=version_payload,
    method='PUT',
    headers={
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }
)
try:
    ssl_context = ssl._create_unverified_context()
except:
    ssl_context = None
try:
    with urllib.request.urlopen(req, timeout=15, context=ssl_context) as res:
        print("[SUCCESS] Firebase update_info.json 업로드 완료")
except Exception as fe:
    print(f"[FAIL] Firebase 업로드 실패: {fe}")

print("\n[5단계] GitHub로 업로드 중...")
try:
    subprocess.run([git_exe, "add", "."], check=True, cwd=BASE_DIR)
    # commit이 실패해도(변경사항 없음) 에러를 무시하도록 처리
    subprocess.run([git_exe, "commit", "-m", f"Release v{new_v}"], check=False, cwd=BASE_DIR)
    # push는 실패하면 에러를 띄움
    result = subprocess.run([git_exe, "push", "origin", "main"], capture_output=True, text=True, cwd=BASE_DIR)
    if result.returncode == 0:
        print(f"\n[성공] 배포 완료! GitHub에 버전 {new_v}이(가) 업로드되었습니다.")
    else:
        print(f"\n[Error] GitHub 업로드 실패 (Push Error).")
        print(result.stderr)
        print("\n로그인이 필요하거나 권한이 없습니다. 바탕화면의 1_깃허브_최초로그인을 다시 실행해 보세요.")
except Exception as e:
    print(f"\n[Error] Git 실행 중 알 수 없는 오류 발생: {e}")

print("\n배포 프로세스가 완료되었습니다.")
input("\n엔터를 누르면 창이 닫힙니다...")
