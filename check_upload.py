with open("github_deploy.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "exe " in line or "upload_url =" in line:
        print("".join(lines[max(0, i-5):i+15]))
        break
