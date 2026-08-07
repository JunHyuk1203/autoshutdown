import sys
sys.stdout.reconfigure(encoding="utf-8")

with open("dashboard.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if "&quot;" in line and "revokeUser" in line:
        print(f"L{i}: {repr(line)}")
