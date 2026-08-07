import requests
import json
import urllib.request
import urllib.error
from io import BytesIO
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
        
        if "firebaseio.com" in url:
            try:
                print(f"[PATCH] Intercepting {method} {url}")
                if method == 'GET':
                    res = _global_session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                elif method == 'PATCH':
                    res = _global_session.patch(url, data=data, headers=headers, timeout=timeout, allow_redirects=True)
                elif method == 'PUT':
                    res = _global_session.put(url, data=data, headers=headers, timeout=timeout, allow_redirects=True)
                elif method == 'POST':
                    res = _global_session.post(url, data=data, headers=headers, timeout=timeout, allow_redirects=True)
                elif method == 'DELETE':
                    res = _global_session.delete(url, headers=headers, timeout=timeout, allow_redirects=True)
                else:
                    return _original_urlopen(url_or_req, *args, **kwargs)
                
                print(f"[PATCH] Response {res.status_code}")
                if res.status_code >= 400:
                    raise urllib.error.HTTPError(url, res.status_code, res.reason, res.headers, BytesIO(res.content))
                    
                return MockResponse(res.content, res.status_code)
            except urllib.error.HTTPError:
                raise
            except Exception as e:
                print(f"[PATCH] Exception: {e}")
                pass
    return _original_urlopen(url_or_req, *args, **kwargs)

urllib.request.urlopen = _fast_urlopen

central_url = "https://atss-a1f9e-default-rtdb.firebaseio.com"
pc_id = "test_pc_123"
import time
timestamp = time.time()

# 1. Simulate web UI push
push_url = f"{central_url}/commands/{pc_id}.json"
r = requests.post(push_url, json={"action": "bring_to_front", "timestamp": timestamp})
push_id = r.json().get("name")
print("Pushed command with ID:", push_id)

# 2. Simulate PC fetching
cmd_url = f"{central_url}/commands/{pc_id}.json"
cmd_req = urllib.request.Request(cmd_url, method='GET')
with urllib.request.urlopen(cmd_req) as res:
    cmd = json.loads(res.read().decode('utf-8'))
    print("Fetched cmd:", cmd)

# 3. Simulate PC deleting
del_url = f"{central_url}/commands/{pc_id}/{push_id}.json"
del_req = urllib.request.Request(del_url, method='DELETE')
try:
    with urllib.request.urlopen(del_req) as res:
        print("DELETE success!")
except Exception as e:
    print("DELETE failed:", e)

# 4. Fetch again to verify
cmd_req2 = urllib.request.Request(cmd_url, method='GET')
with urllib.request.urlopen(cmd_req2) as res:
    cmd2 = json.loads(res.read().decode('utf-8'))
    print("Fetched cmd again:", cmd2)

