import os
import subprocess

print("=" * 50)
print("GitHub 최초 로그인 스크립트")
print("=" * 50)
print("잠시 후 깃허브 로그인 팝업이나 웹 브라우저가 열립니다.")
print("반드시 [Sign in with your browser] 버튼을 클릭해서 권한을 승인해 주세요!")
print("-" * 50)

git_exe = r"C:\Program Files\Git\cmd\git.exe"
if not os.path.exists(git_exe):
    git_exe = "git"

subprocess.run([git_exe, "push", "-u", "origin", "main"])

print("-" * 50)
print("완료되었습니다. 오류 메시지가 없다면 창을 닫고 github_deploy.py를 실행하세요.")
os.system("pause")
