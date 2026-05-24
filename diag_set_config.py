"""
실시간 진단: 웹에서 보낸 set_config 명령이 exe에 의해 소비되는지 확인
"""
import json
import time
import urllib.request
import urllib.error
import ssl
import os

firebase_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/"
pc_id = "PC"
ssl_context = ssl._create_unverified_context()

def fb_read(path):
    url = f"{firebase_url.rstrip('/')}/{path}.json"
    req = urllib.request.Request(url, method='GET')
    with urllib.request.urlopen(req, timeout=5, context=ssl_context) as res:
        return json.loads(res.read().decode('utf-8'))

def fb_write(path, data):
    url = f"{firebase_url.rstrip('/')}/{path}.json"
    payload = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=payload, method='PUT',
                                headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=5, context=ssl_context) as res:
        return json.loads(res.read().decode('utf-8'))

def fb_delete(path):
    url = f"{firebase_url.rstrip('/')}/{path}.json"
    req = urllib.request.Request(url, method='DELETE')
    with urllib.request.urlopen(req, timeout=5, context=ssl_context) as res:
        pass

# 1단계: 기존 명령 정리
print("=" * 60)
print("[1/5] 기존 대기 명령 정리 중...")
try:
    existing = fb_read(f"commands/{pc_id}")
    if existing:
        print(f"     기존 명령 발견: action={existing.get('action')}")
        fb_delete(f"commands/{pc_id}")
        print("     -> 삭제 완료")
    else:
        print("     대기 명령 없음 (정상)")
except Exception as e:
    print(f"     오류: {e}")

time.sleep(1)

# 2단계: 테스트 set_config 명령 전송
print()
print("[2/5] 테스트 set_config 명령 Firebase에 기록 중...")
test_marker = int(time.time())  # 고유 마커
test_cmd = {
    "action": "set_config",
    "message": {
        "minutes_before": 3,
        "show_popup_alert": True
    }
}
fb_write(f"commands/{pc_id}", test_cmd)
print(f"     -> 기록 완료 (minutes_before=3, show_popup_alert=True)")

# 3단계: exe가 소비하는지 대기 (최대 15초)
print()
print("[3/5] exe가 명령을 소비하는지 모니터링 중 (최대 15초)...")
consumed = False
for i in range(15):
    time.sleep(1)
    try:
        remaining = fb_read(f"commands/{pc_id}")
        if remaining is None:
            print(f"     -> {i+1}초 후 명령 소비 확인! (Firebase에서 삭제됨)")
            consumed = True
            break
        else:
            action = remaining.get('action', '?')
            print(f"     {i+1}초... 아직 남아있음 (action={action})")
    except Exception as e:
        print(f"     {i+1}초... 오류: {e}")

if not consumed:
    print()
    print("!!! 경고: exe가 15초 동안 명령을 소비하지 않았습니다 !!!")
    print("    가능한 원인:")
    print("    1) auto_shutdown.exe가 꺼져 있거나 폴링이 중단됨")
    print("    2) set_config 핸들러에서 오류 발생")
    print("    3) 두 번째 exe 인스턴스가 명령을 가로채서 처리 실패")

# 4단계: 실행 중인 exe의 error.log 확인
print()
print("[4/5] dist/error.log 최근 항목 확인...")
error_log = os.path.join("dist", "error.log")
if os.path.exists(error_log):
    with open(error_log, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    # 마지막 10줄
    recent = lines[-10:] if len(lines) >= 10 else lines
    for line in recent:
        line = line.strip()
        if line:
            print(f"     {line}")
else:
    print("     error.log 파일 없음")

# 5단계: dist/schedule_config.json 확인
print()
print("[5/5] dist/schedule_config.json 현재 값 확인...")
dist_cfg = os.path.join("dist", "schedule_config.json")
if os.path.exists(dist_cfg):
    with open(dist_cfg, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    print(f"     minutes_before: {cfg.get('minutes_before')}")
    print(f"     show_popup_alert: {cfg.get('show_popup_alert')}")
    print(f"     autostart: {cfg.get('autostart')}")
    print(f"     school_info.name: {cfg.get('school_info', {}).get('name')}")
    # 레거시 키 존재 여부
    legacy_keys = [k for k in cfg if k in ('central_server_url', 'ngrok_token', 'ngrok_domain', 'is_server')]
    if legacy_keys:
        print(f"     ⚠️ 레거시 키 잔존: {legacy_keys}")
else:
    print("     schedule_config.json 파일 없음")

print()
print("=" * 60)
if consumed:
    print("결론: exe가 명령을 소비했습니다. dist/schedule_config.json 값이")
    print("      minutes_before=3 으로 바뀌었는지 위에서 확인하세요.")
else:
    print("결론: exe가 명령을 소비하지 못했습니다. 근본적 문제가 있습니다.")
