import requests
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()
session.verify = False

central_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/"
pc_id = "test_pc_123"

# 1. Create a dummy command
put_url = f"{central_url}/commands/{pc_id}/dummy.json"
print("PUT:", put_url)
r = session.put(put_url, json={"action": "test"})
print("PUT Result:", r.status_code, r.text)

# 2. Try to GET
r2 = session.get(f"{central_url}/commands/{pc_id}.json")
print("GET Result:", r2.status_code, r2.text)

# 3. Try to DELETE with allow_redirects=True
del_url = put_url
print("DELETE:", del_url)
try:
    r3 = session.delete(del_url, timeout=6, allow_redirects=True)
    print("DELETE Result:", r3.status_code, r3.text)
except Exception as e:
    print("DELETE Exception:", e)

# 4. Try to GET again to verify
r4 = session.get(f"{central_url}/commands/{pc_id}.json")
print("GET2 Result:", r4.status_code, r4.text)

