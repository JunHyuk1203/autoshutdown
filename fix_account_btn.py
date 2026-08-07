with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

btn_html = '<button class="btn-icon" id="account-header-btn" onclick="openAccountModal()" title="계정 관리" style="display:none">&#x1F464;</button>'
text = text.replace('<button class="btn-icon" id="logout-header-btn"', btn_html + '\n            <button class="btn-icon" id="logout-header-btn"')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
