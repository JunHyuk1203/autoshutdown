import sys
sys.stdout.reconfigure(encoding="utf-8")

with open("dashboard.html", "r", encoding="utf-8") as f:
    text = f.read()

# Extract script content between <script> and </script>
import re
scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)
print(f"Found {len(scripts)} script blocks")

# Extract all JS to a temp file
with open("temp_check.js", "w", encoding="utf-8") as f:
    for i, s in enumerate(scripts):
        f.write(f"\n// === SCRIPT BLOCK {i+1} ===\n")
        f.write(s)

print("Written to temp_check.js")
