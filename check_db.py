import json, urllib.request

try:
    req = urllib.request.Request('http://localhost:8000/dashboard.html')
    response = urllib.request.urlopen(req)
    html = response.read().decode('utf-8')
    
    # Extract the database URL
    import re
    db_url_match = re.search(r'databaseURL:\s*"([^"]+)"', html)
    if db_url_match:
        db_url = db_url_match.group(1)
        print(f"DB URL: {db_url}")
        
        users_req = urllib.request.Request(f"{db_url}/users.json")
        users_res = urllib.request.urlopen(users_req)
        users_data = json.loads(users_res.read().decode('utf-8'))
        
        print("Users in DB:")
        for uid, info in (users_data or {}).items():
            print(f" - {uid}: {info}")
    else:
        print("Could not find databaseURL in dashboard.html")
except Exception as e:
    print(f"Error: {e}")
