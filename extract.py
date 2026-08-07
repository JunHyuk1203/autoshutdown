import sys, re
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)

with open("temp.js", "w", encoding="utf-8") as f:
    f.write("\n".join(scripts))
