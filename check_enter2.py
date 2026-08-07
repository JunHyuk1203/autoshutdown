import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find('function _enterDashboard')
end = text.find('config.databaseURL', start)
print(text[start:end+300])
