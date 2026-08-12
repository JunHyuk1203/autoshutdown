with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def open_autologin_settings(" in line:
        print("".join(lines[i:i+5]))
        break
