import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix caching issues with GET requests
text = text.replace('fetch(FB_PROJECT.databaseURL + "/users.json")', 'fetch(FB_PROJECT.databaseURL + "/users.json?_t=" + Date.now())')
text = text.replace('fetch(FB_PROJECT.databaseURL + "/pending_users.json")', 'fetch(FB_PROJECT.databaseURL + "/pending_users.json?_t=" + Date.now())')
text = text.replace('let url = `${config.databaseURL}/pcs.json`;', 'let url = `${config.databaseURL}/pcs.json?_t=` + Date.now();')
# Also handle if authKey is present: we append with & instead of ?
text = text.replace('url += `?auth=${config.authKey}`;', 'url += `&auth=${config.authKey}`;')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
