"""
웹에서 set_config 보내면 exe가 받아서 반영되는지 전체 흐름 테스트
"""
import json
import urllib.request
import ssl
import socket
import time

firebase_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/"
ssl_ctx = ssl._create_unverified_context()

pc_id = socket.gethostname()
for char in [".", "$", "#", "[", "]", "/"]:
    pc_id = pc_id.replace(char, "-")

print(f"PC ID: {pc_id}")
print("=" * 60)

# 1. 기존 명령 정리
try:
    del_url = firebase_url.rstrip("/") + "/commands/" + pc_id + ".json"
    req = urllib.request.Request(del_url, method="DELETE")
    urllib.request.urlopen(req, timeout=5, context=ssl_ctx)
    print("[1] 기존 명령 정리 완료")
except Exception as e:
    print(f"[1] 정리 오류 (무시): {e}")

time.sleep(0.5)

# 2. set_config 전송 (minutes_before=7, show_popup_alert=False)
cmd = {
    "action": "set_config",
    "message": {
        "minutes_before": 7,
        "show_popup_alert": False
    }
}
url = firebase_url.rstrip("/") + "/commands/" + pc_id + ".json"
data = json.dumps(cmd).encode("utf-8")
req = urllib.request.Request(url, data=data, method="PUT",
                              headers={"Content-Type": "application/json"})
urllib.request.urlopen(req, timeout=5, context=ssl_ctx)
print("[2] set_config 전송: minutes_before=7, show_popup_alert=False")

# 3. exe가 소비하는지 최대 15초 대기
print("[3] exe 소비 대기 중 (최대 15초)...")
consumed = False
for i in range(15):
    time.sleep(1)
    chk_url = firebase_url.rstrip("/") + "/commands/" + pc_id + ".json"
    req2 = urllib.request.Request(chk_url, method="GET")
    with urllib.request.urlopen(req2, timeout=5, context=ssl_ctx) as r:
        val = json.loads(r.read())
    if val is None:
        print(f"   -> {i+1}초 후 소비 확인!")
        consumed = True
        break
    else:
        print(f"   {i+1}초 경과... 아직 대기 중")

print()
if not consumed:
    print("!!! exe가 명령을 소비하지 않았습니다. auto_shutdown.exe 실행 여부 확인 필요!")
else:
    # 4. 실제 config 파일 확인
    import os
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "dist", "schedule_config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        mb = cfg.get("minutes_before", "N/A")
        spa = cfg.get("show_popup_alert", "N/A")
        print(f"[4] dist/schedule_config.json 결과:")
        print(f"    minutes_before   = {mb}  (기대: 7)")
        print(f"    show_popup_alert = {spa}  (기대: False)")
        if mb == 7 and spa == False:
            print("\n    [SUCCESS] 설정이 완벽하게 반영되었습니다!")
        else:
            print("\n    [FAIL] 값이 기대와 다릅니다!")
    else:
        print("[4] schedule_config.json 파일이 없습니다!")

    # 5. Firebase pcs 노드의 config 확인
    try:
        pcs_url = firebase_url.rstrip("/") + "/pcs/" + pc_id + ".json"
        req3 = urllib.request.Request(pcs_url, method="GET")
        with urllib.request.urlopen(req3, timeout=5, context=ssl_ctx) as r:
            d = json.loads(r.read())
        c = d.get("config", {})
        print(f"\n[5] Firebase /pcs/{pc_id}/config 결과:")
        print(f"    minutes_before   = {c.get('minutes_before', 'N/A')}")
        print(f"    show_popup_alert = {c.get('show_popup_alert', 'N/A')}")
    except Exception as e:
        print(f"\n[5] Firebase pcs 읽기 오류: {e}")
