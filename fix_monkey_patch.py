import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

# Fix allow_redirects=True
target_code = """                    if method == 'GET':
                        res = _global_session.get(url, headers=headers, timeout=timeout)
                    elif method == 'PATCH':
                        res = _global_session.patch(url, data=data, headers=headers, timeout=timeout)
                    elif method == 'PUT':
                        res = _global_session.put(url, data=data, headers=headers, timeout=timeout)
                    elif method == 'POST':
                        res = _global_session.post(url, data=data, headers=headers, timeout=timeout)
                    elif method == 'DELETE':
                        res = _global_session.delete(url, headers=headers, timeout=timeout)"""

replacement_code = """                    if method == 'GET':
                        res = _global_session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                    elif method == 'PATCH':
                        res = _global_session.patch(url, data=data, headers=headers, timeout=timeout, allow_redirects=True)
                    elif method == 'PUT':
                        res = _global_session.put(url, data=data, headers=headers, timeout=timeout, allow_redirects=True)
                    elif method == 'POST':
                        res = _global_session.post(url, data=data, headers=headers, timeout=timeout, allow_redirects=True)
                    elif method == 'DELETE':
                        res = _global_session.delete(url, headers=headers, timeout=timeout, allow_redirects=True)"""

if target_code in text:
    text = text.replace(target_code, replacement_code)
    print("Monkey patch fixed: Added allow_redirects=True")
else:
    print("Could not find monkey patch to fix!")

text = text.replace('CURRENT_VERSION = "1.1.134"', 'CURRENT_VERSION = "1.1.135"')
text = text.replace('CURRENT_VERSION = "1.1.133"', 'CURRENT_VERSION = "1.1.135"')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = re.sub(r'1\.1\.13[43]', '1.1.135', vtext)
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)

