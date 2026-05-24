import urllib.request
import json
import ssl
import socket

firebase_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/"
pc_id = socket.gethostname()
for char in [".", "$", "#", "[", "]", "/"]:
    pc_id = pc_id.replace(char, "-")

print(f"PC ID (Sanitized): {pc_id}")

ssl_context = ssl._create_unverified_context()

try:
    pcs_url = f"{firebase_url.rstrip('/')}/pcs/{pc_id}.json"
    req = urllib.request.Request(pcs_url, method='GET')
    with urllib.request.urlopen(req, timeout=5, context=ssl_context) as res:
        data = json.loads(res.read().decode('utf-8'))
        print("\n=== Firebase /pcs/{pc_id} ===")
        print(json.dumps(data, indent=4, ensure_ascii=False))
except Exception as e:
    print(f"Failed to read /pcs/{pc_id}: {e}")

try:
    cmd_url = f"{firebase_url.rstrip('/')}/commands/{pc_id}.json"
    req = urllib.request.Request(cmd_url, method='GET')
    with urllib.request.urlopen(req, timeout=5, context=ssl_context) as res:
        data = json.loads(res.read().decode('utf-8'))
        print("\n=== Firebase /commands/{pc_id} ===")
        print(json.dumps(data, indent=4, ensure_ascii=False))
except Exception as e:
    print(f"Failed to read /commands/{pc_id}: {e}")
