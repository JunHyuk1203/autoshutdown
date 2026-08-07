import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find('async function _checkAdminPermission')
end = text.find('}', start + 500)
print(text[start:end+100])
