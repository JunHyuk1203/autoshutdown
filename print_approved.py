import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find('function loadApprovedUsers')
end = text.find('function loadPendingUsers')
print(text[start:end])
