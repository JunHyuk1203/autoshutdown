import json
import os
import urllib.request
import urllib.parse
import ssl

CONFIG_FILE = "schedule_config.json"
central_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/"
pc_id = "PC"

ssl_context = ssl._create_unverified_context()

# 1. 시뮬레이션할 원격 set_config 페이로드 정의
test_message = {
    "minutes_before": 7,
    "autostart": True,
    "show_popup_alert": True,
    "school_info": {
        "name": "마산중앙고등학교",
        "office_code": "S10",
        "school_code": "7005001",
        "school_kind": "고등학교",
        "grade": "2",
        "class_nm": "3",
        "api_key": "4f7314e020ab4adcad7f6aaf048f5944"
    },
    "월": {
        "1교시 (08:40)": {"enabled": True, "action": "시스템 종료"},
        "방과후_기타 (16:30)": {"enabled": True, "action": "절전 모드"}
    }
}

print("1. Firebase에 테스트 원격 설정 명령어 (set_config) 전송 시도...")
cmd_payload = json.dumps({
    "action": "set_config",
    "message": test_message
}).encode('utf-8')

cmd_url = f"{central_url.rstrip('/')}/commands/{pc_id}.json"
req = urllib.request.Request(
    cmd_url,
    data=cmd_payload,
    method='PUT',
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req, timeout=5, context=ssl_context) as res:
        print("-> 성공적으로 명령어를 commands/PC.json 에 기록했습니다.")
except Exception as e:
    print(f"-> 명령어 기록 실패: {e}")
    exit(1)

# 2. 로컬 파싱 알고리즘 시뮬레이션
print("\n2. 수신된 명령어 로컬 파싱 시뮬레이션 시작...")
try:
    # commands/PC.json 에서 명령어 읽어오기
    req_get = urllib.request.Request(cmd_url, method='GET')
    with urllib.request.urlopen(req_get, timeout=5, context=ssl_context) as res:
        cmd = json.loads(res.read().decode('utf-8'))
        
    if cmd and cmd.get("action") == "set_config":
        message = cmd.get("message", {})
        print(f"-> 명령어 수신 성공. message 타입: {type(message)}")
        
        current = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                current = json.load(f)
        
        message_clean = {}
        DAYS = ["월", "화", "수", "목", "금", "토", "일"]
        
        for k, v in message.items():
            if k in DAYS and isinstance(v, dict):
                if k not in current:
                    current[k] = {}
                message_clean[k] = {}
                for period, p_data in v.items():
                    orig_period = period.replace("_", "/") # De-sanitize
                    current[k][orig_period] = p_data
                    message_clean[k][orig_period] = p_data
            else:
                message_clean[k] = v
                if isinstance(v, dict) and k in current and isinstance(current[k], dict):
                    current[k].update(v)
                else:
                    current[k] = v
                    
        # schedule_config.json 에 쓰기
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(current, f, ensure_ascii=False, indent=4)
            
        print("-> schedule_config.json에 설정값 갱신 및 파일 저장 완료!")
        
        # 저장된 결과 검증
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        print("\n=== schedule_config.json 결과 ===")
        print(f"minutes_before: {saved_data.get('minutes_before')}")
        print(f"school_info: {saved_data.get('school_info')}")
        print(f"월 스케줄: {saved_data.get('월')}")
        
except Exception as e:
    print(f"-> 파싱 및 로컬 저장 시뮬레이션 중 오류 발생: {e}")
