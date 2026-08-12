import urllib.request
import json
import ssl

with open("version.json", "r", encoding="utf-8") as f:
    version_data = json.load(f)

firebase_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/update_info.json"
version_payload = json.dumps(version_data).encode("utf-8")

try:
    ssl_context = ssl._create_unverified_context()
    ssl_context.verify_mode = ssl.CERT_NONE
except AttributeError:
    ssl_context = None

req = urllib.request.Request(
    firebase_url,
    data=version_payload,
    method="PUT",
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=10, context=ssl_context) as res:
        print("Success!", res.read().decode("utf-8"))
except Exception as e:
    print("Failed:", e)
