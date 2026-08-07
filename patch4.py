import sys
import re

with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Replace _lastCmdTime logic with an array-based rate limiter
target_rate_limit_var = "let _lastCmdTime = 0;"
replacement_rate_limit_var = "let _cmdTimestamps = [];"

if target_rate_limit_var in text:
    text = text.replace(target_rate_limit_var, replacement_rate_limit_var)

target_rate_limit_logic = """    // Rate Limit (Only for actual commands, not data fetching)
    if (action !== "list_dir" && action !== "get_processes") {
        const now = Date.now();
        if (now - _lastCmdTime < 2000 && _fbAuth?.currentUser?.email && _fbAuth?.currentUser?.email.toLowerCase() !== MASTER_EMAIL.toLowerCase()) {
            alert("명령은 2초에 한 번씩만 전송할 수 있습니다. (연속 클릭 방지)");
            return { success: false };
        }
        _lastCmdTime = now;
    }"""
    
replacement_rate_limit_logic = """    // Rate Limit (Only for actual commands, not data fetching)
    if (action !== "list_dir" && action !== "get_processes") {
        const now = Date.now();
        if (_fbAuth?.currentUser?.email && _fbAuth?.currentUser?.email.toLowerCase() !== MASTER_EMAIL.toLowerCase()) {
            _cmdTimestamps.push(now);
            // 10초가 지난 타임스탬프는 제거
            _cmdTimestamps = _cmdTimestamps.filter(t => now - t <= 10000);
            
            // 10초 내 20회 이상 발생 시 차단
            if (_cmdTimestamps.length >= 20) {
                triggerSecurityViolation("비정상 연속 제어 명령 감지 (10초 내 20회 이상)");
                return { success: false };
            }
        }
    }"""
    
if target_rate_limit_logic in text:
    text = text.replace(target_rate_limit_logic, replacement_rate_limit_logic)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("rate limit updated")
