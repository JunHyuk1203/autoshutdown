import sys, re
sys.stdout.reconfigure(encoding="utf-8")

with open("dashboard.html", "r", encoding="utf-8") as f:
    text = f.read()

# Check for any remaining HTML entities in JS context (inside template literals or onclick)
issues = []
lines = text.split("\n")
for i, line in enumerate(lines, 1):
    if ("&quot;" in line or "&apos;" in line or "&#039;" in line) and ("onclick" in line or "innerHTML" in line or "`" in line):
        issues.append(f"L{i}: {line.strip()[:200]}")

if issues:
    print(f"Found {len(issues)} potentially problematic lines:")
    for issue in issues:
        print(issue)
else:
    print("No HTML entity issues found in JS/template contexts!")
