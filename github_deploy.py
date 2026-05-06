import os
import re
import json
import subprocess
import time

print("="*50)
print("🚀 [스마트 전원 관리자] 배포 자동화 프로그램")
print("="*50)

app_path = "auto_shutdown.py"
if not os.path.exists(app_path):
    print(f"❌ {app_path} 파일을 찾을 수 없습니다.")
    time.sleep(3)
    exit(1)

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

version_match = re.search(r'CURRENT_VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
if not version_match:
    print("❌ 버전 정보(CURRENT_VERSION)를 찾을 수 없습니다.")
    time.sleep(3)
    exit(1)

major, minor, patch = int(version_match.group(1)), int(version_match.group(2)), int(version_match.group(3))
current_v = f"{major}.{minor}.{patch}"
new_v = f"{major}.{minor}.{patch+1}"

print(f"\n📦 1단계: 버전 업그레이드 ({current_v} -> {new_v})")
content = content.replace(f'CURRENT_VERSION = "{current_v}"', f'CURRENT_VERSION = "{new_v}"')
with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n🔨 2단계: 기존 실행 중인 프로그램 강제 종료 중...")
try:
    subprocess.run(["taskkill", "/F", "/IM", "auto_shutdown.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except:
    pass
time.sleep(1)

print("\n🔨 3단계: PyInstaller 빌드 중... (시간이 걸릴 수 있습니다)")
try:
    subprocess.run(["pyinstaller", "--noconfirm", "auto_shutdown.spec"], check=True)
except Exception as e:
    print(f"❌ 빌드 실패: {e}")
    # 원상 복구
    content = content.replace(f'CURRENT_VERSION = "{new_v}"', f'CURRENT_VERSION = "{current_v}"')
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(content)
    time.sleep(3)
    exit(1)

print("\n📝 4단계: version.json 업데이트 중...")
version_data = {
    "version": new_v,
    "download_url": "https://raw.githubusercontent.com/JunHyuk1203/autoshutdown/main/dist/auto_shutdown.exe"
}
with open("version.json", "w", encoding="utf-8") as f:
    json.dump(version_data, f, indent=4)

print("\n☁️ 5단계: GitHub로 업로드 중...")
try:
    git_exe = r"C:\Program Files\Git\cmd\git.exe"
    subprocess.run([git_exe, "add", "."], check=True)
    subprocess.run([git_exe, "commit", "-m", f"🚀 Release v{new_v}"], check=True)
    subprocess.run([git_exe, "push", "origin", "main"], check=True)
    print(f"\n✅ 배포 성공! GitHub에 버전 {new_v}이(가) 업로드되었습니다.")
except Exception as e:
    print(f"\n❌ GitHub 업로드 실패: {e}")
    print("git 로그인이 되어있는지, 원격 저장소에 쓰기 권한이 있는지 확인하세요.")

print("\n창을 닫으려면 아무 키나 누르세요...")
os.system("pause > nul")
