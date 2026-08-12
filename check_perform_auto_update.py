with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def perform_auto_update(" in line:
        print("".join(lines[i:i+60]))
        break
