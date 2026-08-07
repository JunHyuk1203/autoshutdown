import sys, re
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)
for i, s in enumerate(scripts):
    print(f"Script {i} length: {len(s)}")
    if "MASTER_EMAIL" in s:
        print(f"  -> Contains MASTER_EMAIL")
    if "loadApprovedUsers" in s:
        print(f"  -> Contains loadApprovedUsers")
