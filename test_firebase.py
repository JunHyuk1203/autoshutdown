import urllib.request
import json
import ssl
import socket
import traceback

firebase_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/"
pc_id = socket.gethostname()
for char in [".", "$", "#", "[", "]", "/"]:
    pc_id = pc_id.replace(char, "-")

print(f"PC ID: {pc_id}")
print(f"Firebase URL: {firebase_url}")

payload = json.dumps({
    'ip': '192.168.0.1',
    'hostname': pc_id,
    'user': 'test',
    'version': '1.0',
    'status': 'online',
    'next_event': 'test',
    'last_seen': '12:00:00',
    'last_seen_ts': 1234567890.0,
}).encode('utf-8')

ssl_context = ssl._create_unverified_context()

# Test 1: PATCH with urllib (original method)
print("\n--- Test 1: urllib PATCH ---")
patch_url = f"{firebase_url.rstrip('/')}/pcs/{pc_id}.json"
print(f"URL: {patch_url}")
try:
    req = urllib.request.Request(
        patch_url,
        data=payload,
        method='PATCH',
        headers={
            'Content-Type': 'application/json',
            'Content-Length': str(len(payload))
        }
    )
    print(f"Method: {req.get_method()}")
    print(f"Headers: {req.headers}")
    print(f"Data length: {len(payload)}")
    with urllib.request.urlopen(req, timeout=10, context=ssl_context) as res:
        print(f"SUCCESS! Status: {res.status}")
        print(f"Response: {res.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
    body = e.read().decode('utf-8', errors='replace')
    print(f"Response Body: {body}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()

# Test 2: PUT instead of PATCH
print("\n--- Test 2: urllib PUT ---")
try:
    req2 = urllib.request.Request(
        patch_url,
        data=payload,
        method='PUT',
        headers={
            'Content-Type': 'application/json',
            'Content-Length': str(len(payload))
        }
    )
    with urllib.request.urlopen(req2, timeout=10, context=ssl_context) as res:
        print(f"SUCCESS! Status: {res.status}")
        print(f"Response: {res.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
    body = e.read().decode('utf-8', errors='replace')
    print(f"Response Body: {body}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()

# Test 3: PATCH via X-HTTP-Method-Override
print("\n--- Test 3: POST with X-HTTP-Method-Override: PATCH ---")
try:
    req3 = urllib.request.Request(
        patch_url,
        data=payload,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'Content-Length': str(len(payload)),
            'X-HTTP-Method-Override': 'PATCH'
        }
    )
    with urllib.request.urlopen(req3, timeout=10, context=ssl_context) as res:
        print(f"SUCCESS! Status: {res.status}")
        print(f"Response: {res.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
    body = e.read().decode('utf-8', errors='replace')
    print(f"Response Body: {body}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
