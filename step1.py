import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add escapeHtml globally
if 'function escapeHtml(' not in text:
    escape_fn = """
// HTML XSS 방지용 이스케이프 함수
function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') return unsafe;
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}
"""
    text = text.replace('// --- 전역 변수 ---', escape_fn + '\n// --- 전역 변수 ---')

# 2. Change <input type="text"> for config keys to password
text = text.replace('id="cfg-api-key" class="config-input"', 'id="cfg-api-key" type="password" class="config-input"')
text = text.replace('id="cfg-auth-key" class="config-input"', 'id="cfg-auth-key" type="password" class="config-input"')

with open('dashboard_tmp.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Applied Step 1 & 2")
