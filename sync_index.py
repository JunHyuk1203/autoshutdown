# -*- coding: utf-8 -*-
"""Sync open-file modal + JS changes from dashboard.html to index.html"""

with open('dashboard.html', 'r', encoding='utf-8') as f:
    d = f.read()

with open('index.html', 'r', encoding='utf-8') as f:
    idx = f.read()

# ── 1. Sync the modal HTML ────────────────────────────────────────────────
MODAL_START = '<div class="modal-overlay" id="open-file-modal">'
MODAL_END_ANCHOR = '<!-- ─────────────────────────────────────────────────────────────\n   실행 중인 창 목록 모달'

d_ms = d.find(MODAL_START)
d_me = d.find(MODAL_END_ANCHOR)
modal_html = d[d_ms:d_me]

idx_ms = idx.find(MODAL_START)
idx_me = idx.find(MODAL_END_ANCHOR)

new_idx = idx[:idx_ms] + modal_html + idx[idx_me:]

# ── 2. Sync the JS section ────────────────────────────────────────────────
JS_START = 'let _ofCurrentTab'
JS_END_ANCHOR = '</script>'

d_jss = d.rfind(JS_START)
d_jse = d.rfind(JS_END_ANCHOR)
js_section = d[d_jss:d_jse]  # does NOT include </script>

# Find old JS in new_idx
OLD_JS_MARKERS = [
    '/** 파일 열기 명령 전송 */',
    'async function sendOpenFileCommand',
]
idx_old_js = -1
for marker in OLD_JS_MARKERS:
    idx_old_js = new_idx.rfind(marker)
    if idx_old_js != -1:
        break

idx_old_jse = new_idx.rfind(JS_END_ANCHOR)

if idx_old_js != -1:
    new_idx = new_idx[:idx_old_js] + js_section + new_idx[idx_old_jse:]
else:
    print('WARNING: could not locate JS anchor in index.html')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_idx)

print('index.html synced successfully')
print('  - of-tab-file present:', 'of-tab-file' in new_idx)
print('  - sendOpenUrlCommand present:', 'sendOpenUrlCommand' in new_idx)
