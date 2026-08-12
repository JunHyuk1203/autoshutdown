with open("github_deploy.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "스마트_전원_관리자_설치파일" in line or "installer.spec" in line or "installer_spec" in line:
        print("".join(lines[max(0, i-5):i+20]))
        break
