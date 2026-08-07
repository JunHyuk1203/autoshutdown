import sys
sys.stdout.reconfigure(encoding="utf-8")

with open("temp_check.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the &quot; occurrence which is the HTML-entity causing JS syntax issue
for i, line in enumerate(lines, 1):
    if "&quot;" in line or "&#039;" in line:
        print(f"L{i}: {line}", end="")
