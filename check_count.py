import json, urllib.request

try:
    db_url = "https://atss-a1f9e-default-rtdb.firebaseio.com"
    users_req = urllib.request.Request(f"{db_url}/users.json")
    users_res = urllib.request.urlopen(users_req)
    users_data = json.loads(users_res.read().decode('utf-8'))
    
    count = 0
    for uid, info in (users_data or {}).items():
        is_master = (info.get('email') == "tntgame1203@gmail.com") or (info.get('role') == "master")
        if info.get('approved') is True and not is_master:
            count += 1
            print(f"Matched User: {uid} -> {info.get('email')}")
            
    print(f"Total approved normal users: {count}")
except Exception as e:
    print(f"Error: {e}")
