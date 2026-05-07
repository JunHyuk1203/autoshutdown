import os
import re
import json
import subprocess
import time
import sys

# Windows CMD 인코딩 강제 설정 (CP949 호환을 위해 이모지 제거)
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

print("==================================================")
print("[AutoShutdown] 배포 자동화 프로그램 시작")
print("==================================================")

app_path = "auto_shutdown.py"
if not os.path.exists(app_path):
    print(f"[Error] {app_path} 파일을 찾을 수 없습니다.")
    time.sleep(3)
    exit(1)

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

version_match = re.search(r'CURRENT_VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
if not version_match:
    print("[Error] 버전 정보(CURRENT_VERSION)를 찾을 수 없습니다.")
    time.sleep(3)
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
    subprocess.run(["pyinstaller", "--clean", "--noconfirm", "auto_shutdown.spec"], check=True)
except Exception as e:
    print(f"[Error] 빌드 실패: {e}")
    # 원상 복구
    content = content.replace(f'CURRENT_VERSION = "{new_v}"', f'CURRENT_VERSION = "{current_v}"')
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(content)
    time.sleep(3)
    exit(1)

print("\n[4단계] version.json 업데이트 중...")
version_data = {
    "version": new_v,
    "download_url": "https://raw.githubusercontent.com/JunHyuk1203/autoshutdown/main/dist/auto_shutdown.exe"
}
with open("version.json", "w", encoding="utf-8") as f:
    json.dump(version_data, f, indent=4)

print("\n[5단계] GitHub로 업로드 중...")
git_exe = r"C:\Program Files\Git\cmd\git.exe"

try:
    subprocess.run([git_exe, "add", "."], check=True)
    # commit이 실패해도(변경사항 없음) 에러를 무시하도록 처리
    subprocess.run([git_exe, "commit", "-m", f"Release v{new_v}"], check=False)
    # push는 실패하면 에러를 띄움
    result = subprocess.run([git_exe, "push", "origin", "main"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"\n[성공] 배포 완료! GitHub에 버전 {new_v}이(가) 업로드되었습니다.")
    else:
        print(f"\n[Error] GitHub 업로드 실패 (Push Error).")
        print(result.stderr)
        print("\n로그인이 필요하거나 권한이 없습니다. 바탕화면의 1_깃허브_최초로그인을 다시 실행해 보세요.")
except Exception as e:
    print(f"\n[Error] Git 실행 중 알 수 없는 오류 발생: {e}")

print("\n배포 프로세스가 완료되었습니다.")
