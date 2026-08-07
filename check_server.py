import urllib.request
import json

req = urllib.request.Request('http://localhost:8000/dashboard.html')
response = urllib.request.urlopen(req)
text = response.read().decode('utf-8')
print("dashboard.html is being served, length:", len(text))
