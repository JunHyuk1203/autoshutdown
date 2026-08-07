import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.finditer(r'<script.*?>.*?</script>', text, re.DOTALL)
has_syntax_error = False
for m in matches:
    script_content = m.group(0)
    if 'loadApprovedUsers' in script_content:
        # Check for matching braces manually
        opens = script_content.count('{')
        closes = script_content.count('}')
        print(f"Braces count: {{ {opens}, }} {closes}")
