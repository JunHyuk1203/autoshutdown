import json, urllib.request

try:
    db_url = "https://atss-a1f9e-default-rtdb.firebaseio.com"
    req = urllib.request.Request(f"{db_url}/pending_users.json")
    res = urllib.request.urlopen(req)
    data = json.loads(res.read().decode('utf-8'))
    print(f"Pending Users in DB: {data}")
except Exception as e:
    print(f"Error fetching data: {e}")
