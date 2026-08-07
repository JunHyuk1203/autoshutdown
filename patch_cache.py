import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

target = "headers = dict(req.headers)"
replacement = "headers = dict(req.headers)\n            headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'\n            headers['Pragma'] = 'no-cache'\n            headers['Expires'] = '0'"

if target in text:
    text = text.replace(target, replacement)
    print("Patched headers to bypass cache!")
else:
    print("Could not find headers = dict(req.headers)")

text = text.replace('CURRENT_VERSION = "1.1.140"', 'CURRENT_VERSION = "1.1.141"')
text = text.replace('CURRENT_VERSION = "1.1.139"', 'CURRENT_VERSION = "1.1.141"')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = re.sub(r'1\.1\.140', '1.1.141', vtext)
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)

