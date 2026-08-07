import sys
sys.stdout.reconfigure(encoding="utf-8")

with open("temp_check.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

start = max(0, 1840)
end = min(len(lines), 1870)
for i, line in enumerate(lines[start:end], start+1):
    print(f"L{i}: {line}", end="")
