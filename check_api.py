import urllib.request, json
try:
    req = urllib.request.Request("https://api.github.com/repos/JunHyuk1203/autoshutdown/releases/tags/v1.1.162", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
        for asset in data.get("assets", []):
            print("Found asset:", asset.get("name"))
except Exception as e:
    print("Error:", e)
