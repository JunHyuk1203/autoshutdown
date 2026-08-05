with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('#auth-view, #pending-view, #setup-view, #verify-email-view {', '#auth-view, #pending-view, #setup-view, #verify-email-view, #revoked-view {')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
