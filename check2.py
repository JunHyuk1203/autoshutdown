import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("dashboard.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "_isApproved" in line or "approveUser" in line or "role" in line.lower():
        print(f"L{i+1}: {line.rstrip()}")
