import requests
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()
session.verify = False

central_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/"
pc_id = "test_pc_123"

put_url = f"{central_url}/commands/{pc_id}/dummy.json"

# We must send an auth token or bypass it. Since we are testing if requests.delete works with allow_redirects, let's just make the request.
try:
    r = session.delete(put_url, timeout=6, allow_redirects=True)
    print("Delete status code:", r.status_code)
    print("Delete text:", r.text)
except Exception as e:
    print("Delete Exception:", e)

