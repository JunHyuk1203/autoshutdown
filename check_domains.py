import sys
import re
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

domains = set(re.findall(r'https?://[a-zA-Z0-9.-]+', text))
print("External domains used:")
for d in domains:
    print(d)
