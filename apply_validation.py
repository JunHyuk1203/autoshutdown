import re
import sys
sys.stdout.reconfigure(encoding="utf-8")

with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Inputs validation
replacements = {
    r'id="auth-email-input" type="email" name="email" placeholder="이메일" autocomplete="email"':
    r'id="auth-email-input" type="email" name="email" placeholder="이메일" autocomplete="email" required maxlength="100"',
    
    r'id="auth-pw-input" type="password" name="password" placeholder="비밀번호 (6자리 이상)" autocomplete="current-password"':
    r'id="auth-pw-input" type="password" name="password" placeholder="비밀번호 (6자리 이상)" autocomplete="current-password" required minlength="6" maxlength="32"',

    r'id="account-new-pw" class="auth-input" placeholder="새 비밀번호 (6자리 이상)" style="width:100%; box-sizing:border-box;"':
    r'id="account-new-pw" class="auth-input" placeholder="새 비밀번호 (6자리 이상)" style="width:100%; box-sizing:border-box;" minlength="6" maxlength="32"',
    
    r'id="account-new-pw-confirm" class="auth-input" placeholder="새 비밀번호 확인" style="width:100%; box-sizing:border-box; margin-top:10px;"':
    r'id="account-new-pw-confirm" class="auth-input" placeholder="새 비밀번호 확인" style="width:100%; box-sizing:border-box; margin-top:10px;" minlength="6" maxlength="32"',
    
    r'id="cfg-minutes-before" type="number" min="0" max="60"':
    r'id="cfg-minutes-before" type="number" min="0" max="60" required',
    
    r'id="cfg-school-name" type="text" placeholder="예: 마산중앙고등학교"':
    r'id="cfg-school-name" type="text" placeholder="예: 마산중앙고등학교" maxlength="100"',
    
    r'id="cfg-office-code" type="text" placeholder="예: S10"':
    r'id="cfg-office-code" type="text" placeholder="예: S10" maxlength="10"',
    
    r'id="cfg-class" type="text" placeholder="예: 1"':
    r'id="cfg-class" type="text" placeholder="예: 1" maxlength="10"',
    
    r'id="cfg-api-key" type="password" placeholder="오픈NEIS API Key"':
    r'id="cfg-api-key" type="password" placeholder="오픈NEIS API Key" maxlength="200"',
    
    r'id="explorer-path" type="text" placeholder="경로 입력 (예: C:\\)" style="flex-grow: 1; margin-bottom: 0;" onkeydown="if(event.key===''Enter'') loadExplorerPath()"':
    r'id="explorer-path" type="text" placeholder="경로 입력 (예: C:\\)" style="flex-grow: 1; margin-bottom: 0;" maxlength="500"',
    
    r'id="of-fav-name" type="text" placeholder="예: 수업 PPT, 출석부 등"':
    r'id="of-fav-name" type="text" placeholder="예: 수업 PPT, 출석부 등" maxlength="100"',
    
    r'id="of-url" type="text" placeholder="예: https://www.youtube.com/watch?v=..."':
    r'id="of-url" type="text" placeholder="예: https://www.youtube.com/watch?v=..." maxlength="500"',
    
    r'id="of-url-browser" type="text" placeholder="예: C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"':
    r'id="of-url-browser" type="text" placeholder="예: C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" maxlength="500"',
    
    r'id="wm-search-input" type="text" placeholder="🔍 창 제목 또는 프로그램 검색..." oninput="filterWindowsList()" autocomplete="off" style="flex-grow: 1; margin-bottom: 0;"':
    r'id="wm-search-input" type="text" placeholder="🔍 창 제목 또는 프로그램 검색..." autocomplete="off" style="flex-grow: 1; margin-bottom: 0;" maxlength="100"',
    
    r'id="volume-slider" min="0" max="100" value="50" style="flex-grow: 1; accent-color: var(--primary); cursor: pointer;" oninput="document.getElementById(''volume-value-display'').innerText = this.value + ''%''"':
    r'id="volume-slider" min="0" max="100" value="50" style="flex-grow: 1; accent-color: var(--primary); cursor: pointer;"'
}

for k, v in replacements.items():
    text = text.replace(k, v)

# 2. Extract and remove click handlers that are simple "functionCall()"
handler_map = {}
def replacer(m):
    attr = m.group(1) # onclick, onchange, etc
    func = m.group(2) # handleEmailAuth(), etc
    
    # generate an ID if the element doesn't have one? We can't do that easily with regex here,
    # better to add IDs manually or use a DOM parser.
    return m.group(0)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Validation added!")
