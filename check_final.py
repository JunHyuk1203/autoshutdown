import sys, re
sys.stdout.reconfigure(encoding="utf-8")

with open("dashboard.html", "r", encoding="utf-8") as f:
    text = f.read()

# Check for any remaining HTML entities in JS context
issues = []
lines = text.split("\n")
for i, line in enumerate(lines, 1):
    if ("&quot;" in line or "&apos;" in line) and ("onclick" in line or "`" in line) and "<!-- " not in line:
        issues.append(f"L{i}: {line.strip()[:200]}")

if issues:
    print(f"Found {len(issues)} problematic lines:")
    for issue in issues:
        print(issue)
else:
    print("CLEAN: No HTML entity issues in JS contexts!")
