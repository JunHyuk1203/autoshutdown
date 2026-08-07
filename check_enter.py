import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# find _enterDashboard
start = text.find("function _enterDashboard")
end = text.find("}", start + 200)
print(text[start:end+100])
