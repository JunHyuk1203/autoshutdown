import urllib.request
import json
import ssl

try:
    _ssl = ssl._create_unverified_context()
except Exception:
    _ssl = None

version_data = {
    "version": "1.1.124",
    "download_url": "https://github.com/JunHyuk1203/autoshutdown/releases/download/v1.1.124/auto_shutdown.exe"
}

firebase_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/update_info.json"
version_payload = json.dumps(version_data).encode("utf-8")
fb_req = urllib.request.Request(
    firebase_url, data=version_payload, method="PUT",
    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
)
try:
    with urllib.request.urlopen(fb_req, timeout=15, context=_ssl) as res:
        print("[SUCCESS] Firebase update_info.json 업로드 완료")
except Exception as fe:
    print(f"[FAIL] Firebase 업로드 실패: {fe}")
