import sys, re
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Look for tab buttons
matches = re.findall(r'<button class="admin-tab-btn".*?</button>', text, re.DOTALL)
for m in matches:
    print("Found tab button:", m.strip())
