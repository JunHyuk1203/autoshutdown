with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# We will use regex to find the badge logic block inside loadPendingUsers
# It looks like:
# 

pat = re.compile(r"\$\{info\.requestType === 'reactivation'.*?: '<span.*?신규 가입</span>'\}", re.DOTALL)

new_badge = ''''''

text = re.sub(pat, new_badge, text)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
