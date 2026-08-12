import re
with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()
text = re.sub(r'CURRENT_VERSION = "1\.1\.\d+"', 'CURRENT_VERSION = "1.1.157"', text)
with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)
with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = re.sub(r'1\.1\.\d+', '1.1.157', vtext)
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)
print("1.1.157")
