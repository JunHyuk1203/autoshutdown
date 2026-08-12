import requests

url = "https://atss-a1f9e-default-rtdb.firebaseio.com/update_info.json"
r = requests.get(url)
print("Current update_info on Firebase:", r.status_code, r.text)
