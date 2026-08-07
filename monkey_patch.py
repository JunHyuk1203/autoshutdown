import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

patch_code = """
import urllib.request
import urllib.error
import urllib.parse
import json
import time

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _global_session = requests.Session()
    _global_session.verify = False
    _original_urlopen = urllib.request.urlopen
    
    class MockResponse:
        def __init__(self, content, status):
            self.content = content
            self.status = status
            self.code = status
        def read(self):
            return self.content
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    def _fast_urlopen(url_or_req, *args, **kwargs):
        req = url_or_req
        if isinstance(req, urllib.request.Request):
            url = req.full_url
            method = req.method if req.method else ('POST' if req.data else 'GET')
            headers = dict(req.headers)
            data = req.data
            timeout = kwargs.get('timeout', 10)
            
            # Only intercept Firebase realtime database requests
            if "firebaseio.com" in url:
                try:
                    if method == 'GET':
                        res = _global_session.get(url, headers=headers, timeout=timeout)
                    elif method == 'PATCH':
                        res = _global_session.patch(url, data=data, headers=headers, timeout=timeout)
                    elif method == 'PUT':
                        res = _global_session.put(url, data=data, headers=headers, timeout=timeout)
                    elif method == 'POST':
                        res = _global_session.post(url, data=data, headers=headers, timeout=timeout)
                    elif method == 'DELETE':
                        res = _global_session.delete(url, headers=headers, timeout=timeout)
                    else:
                        return _original_urlopen(url_or_req, *args, **kwargs)
                    
                    if res.status_code >= 400:
                        from io import BytesIO
                        raise urllib.error.HTTPError(url, res.status_code, res.reason, res.headers, BytesIO(res.content))
                        
                    return MockResponse(res.content, res.status_code)
                except urllib.error.HTTPError:
                    raise
                except Exception as e:
                    # If requests fails, just fallback to urllib
                    pass
        return _original_urlopen(url_or_req, *args, **kwargs)

    urllib.request.urlopen = _fast_urlopen
except ImportError:
    pass
"""

# Insert patch_code after the initial imports (around line 15)
if "_fast_urlopen" not in text:
    insert_pos = text.find("import ssl") + len("import ssl\n")
    text = text[:insert_pos] + patch_code + text[insert_pos:]

text = text.replace('CURRENT_VERSION = "1.1.132"', 'CURRENT_VERSION = "1.1.133"')
text = text.replace('CURRENT_VERSION = "1.1.131"', 'CURRENT_VERSION = "1.1.133"')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = re.sub(r'1\.1\.13[12]', '1.1.133', vtext)
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)

print("auto_shutdown.py monkey-patched with requests.Session!")
