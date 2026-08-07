import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("temp_check2.js", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines[1850:1870], 1851):
    print(f"L{i}: {line}", end="")
