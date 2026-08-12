with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "def check_for_updates(" in line or "check_update" in line:
        print("update function found at", i)
