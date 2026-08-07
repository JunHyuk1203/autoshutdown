import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("dashboard.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "approved" in line.lower() or "switchAdminTab" in line:
        print(f"L{i+1}: {line.rstrip()}")
