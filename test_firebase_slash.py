import urllib.request
import json
import ssl

firebase_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/"
ssl_context = ssl._create_unverified_context()

# Test 1: PUT with slash in key
payload_with_slash = json.dumps({
    "action": "set_config",
    "message": {
        "월": {
            "방과후/기타 (16:30)": {
                "enabled": True,
                "action": "시스템 종료"
            }
        }
    }
}).encode('utf-8')

url = f"{firebase_url.rstrip('/')}/commands/TEST_PC.json"
print("Testing PUT with slash in key...")
try:
    req = urllib.request.Request(
        url,
        data=payload_with_slash,
        method='PUT',
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=5, context=ssl_context) as res:
        print(f"SUCCESS! status: {res.status}")
except urllib.error.HTTPError as e:
    print(f"FAILED! code: {e.code}, body: {e.read().decode()}")
except Exception as e:
    print(f"FAILED! error: {e}")
