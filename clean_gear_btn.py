with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
# Remove the gear icon button
pattern = re.compile(r'<button class="btn-icon" onclick="resetConfiguration\(\)" title=".*?">.*?</button>\n', re.DOTALL)
text = re.sub(pattern, '', text)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
