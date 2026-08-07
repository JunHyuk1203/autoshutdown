import json, urllib.request

try:
    db_url = "https://atss-a1f9e-default-rtdb.firebaseio.com"
    users_req = urllib.request.Request(f"{db_url}/users.json")
    users_res = urllib.request.urlopen(users_req)
    users_data = json.loads(users_res.read().decode('utf-8'))
    print("Success: Rules are public!")
except Exception as e:
    print(f"Error fetching data: {e}")
