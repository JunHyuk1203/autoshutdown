import sys, re
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)
js_code = "\n".join(scripts)
with open("test.js", "w", encoding="utf-8") as f:
    f.write(js_code)
