import sys
sys.stdout.reconfigure(encoding="utf-8")

with open("dashboard.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)

with open("temp_check2.js", "w", encoding="utf-8") as f:
    for i, s in enumerate(scripts):
        f.write(f"\n// === SCRIPT BLOCK {i+1} ===\n")
        f.write(s)
