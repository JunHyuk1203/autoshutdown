import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Check the _dashboardInitialized guard and setAccessGranted interaction
start = text.find('window._dashboardInitialized')
print(text[start-50:start+200])
print("---")
start2 = text.find('function setAccessGranted')
print(text[start2:start2+200])
