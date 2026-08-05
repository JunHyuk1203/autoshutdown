import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace all forms of appending auth
text = text.replace('url += `&auth=${config.authKey}`;', 'url += (url.includes("?") ? "&" : "?") + `auth=${config.authKey}`;')
text = text.replace('url += `?auth=${config.authKey}`;', 'url += (url.includes("?") ? "&" : "?") + `auth=${config.authKey}`;')
text = text.replace('+ (config.authKey ? `?auth=${config.authKey}` : "")', '+ (config.authKey ? (url.includes("?") ? `&auth=${config.authKey}` : `?auth=${config.authKey}`) : "")')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
