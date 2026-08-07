import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find('function _showScreen')
end = text.find('function ', start + 100)
print(text[start:end+100])
