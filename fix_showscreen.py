with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('"setup-view","auth-view","verify-email-view","pending-view","onboarding-view","dashboard-view"', '"auth-view","verify-email-view","pending-view","dashboard-view"')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
