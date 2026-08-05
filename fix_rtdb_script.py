with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Add firebase-database-compat.js
old_scripts = '''<!-- Firebase Auth SDK (Compat v10) -->
<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js"></script>'''
new_scripts = '''<!-- Firebase Auth SDK (Compat v10) -->
<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-database-compat.js"></script>'''

text = text.replace(old_scripts, new_scripts)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
