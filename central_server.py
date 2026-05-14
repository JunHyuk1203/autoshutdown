import os
import sys
import json
import time
import socket
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# ──────────────────────────────────────────────
# 데이터 저장소
# ──────────────────────────────────────────────
connected_pcs = {}      # pc_id -> {ip, hostname, last_seen, status, user}
pending_commands = {}   # pc_id -> {action, ...} 또는 "__ALL__" -> {action, ...}
data_lock = threading.Lock()

SERVER_PORT = 5000
BROADCAST_PORT = 5555
OFFLINE_THRESHOLD = 10  # 초 — 이 시간 동안 heartbeat 없으면 오프라인 판정

NGROK_URL = None


def get_local_ip():
    """현재 PC의 LAN IP 주소를 자동 감지"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


# ──────────────────────────────────────────────
# 백그라운드 스레드
# ──────────────────────────────────────────────
def broadcast_thread():
    """UDP 브로드캐스트로 서버 위치를 알림 (클라이언트 자동 감지용)"""
    server_ip = get_local_ip()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    msg = f"SMARTPOWER:{server_ip}:{SERVER_PORT}".encode()
    while True:
        try:
            sock.sendto(msg, ('<broadcast>', BROADCAST_PORT))
        except Exception:
            pass
        time.sleep(2)


def cleanup_thread():
    """오래된 PC를 오프라인으로 전환"""
    while True:
        now = time.time()
        with data_lock:
            for pc_id, info in connected_pcs.items():
                if now - info.get('last_seen_ts', 0) > OFFLINE_THRESHOLD:
                    info['status'] = 'offline'
        time.sleep(3)


# ──────────────────────────────────────────────
# API 엔드포인트
# ──────────────────────────────────────────────
@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """학생 PC가 상태를 보고하고, 대기 중인 명령을 받아감"""
    data = request.get_json(force=True)
    pc_id = data.get('pc_id', 'unknown')
    now_ts = time.time()

    with data_lock:
        connected_pcs[pc_id] = {
            'ip': data.get('ip', request.remote_addr),
            'hostname': data.get('hostname', pc_id),
            'last_seen': datetime.now().strftime('%H:%M:%S'),
            'last_seen_ts': now_ts,
            'status': 'online',
            'user': data.get('user', ''),
        }

        # 대기 중인 명령 확인 (개별 + 전체)
        cmd = None
        if pc_id in pending_commands:
            cmd = pending_commands.pop(pc_id)
        elif '__ALL__' in pending_commands:
            cmd = pending_commands['__ALL__']

    response = {'ok': True}
    if cmd:
        response['command'] = cmd.get('action', '')
        response['message'] = cmd.get('message', '')
    return jsonify(response)


@app.route('/api/pcs')
def get_pcs():
    """현재 연결된 모든 PC 목록 반환"""
    with data_lock:
        pcs = []
        for pc_id, info in sorted(connected_pcs.items()):
            pcs.append({
                'pc_id': pc_id,
                'ip': info.get('ip', ''),
                'hostname': info.get('hostname', ''),
                'last_seen': info.get('last_seen', ''),
                'status': info.get('status', 'offline'),
                'user': info.get('user', ''),
            })
    return jsonify(pcs)


@app.route('/api/send_command', methods=['POST'])
def send_command():
    """관리자가 명령을 보냄"""
    data = request.get_json(force=True)
    target = data.get('target', '__ALL__')   # pc_id 또는 "__ALL__"
    action = data.get('action', '')          # shutdown, sleep, restart, message
    message = data.get('message', '')

    cmd = {'action': action, 'message': message, 'timestamp': time.time()}

    with data_lock:
        if target == '__ALL__':
            # 전체 명령: __ALL__ 키로 저장 (다음 폴링 때 모든 클라이언트가 수신)
            pending_commands['__ALL__'] = cmd
            # 5초 후 자동 삭제 (이미 받아간 클라이언트가 중복 실행하지 않도록)
            threading.Timer(8.0, lambda: pending_commands.pop('__ALL__', None)).start()
        else:
            pending_commands[target] = cmd

    return jsonify({'ok': True, 'target': target, 'action': action})


@app.route('/api/clear_offline', methods=['POST'])
def clear_offline():
    """오프라인 PC 목록에서 제거"""
    with data_lock:
        to_remove = [k for k, v in connected_pcs.items() if v.get('status') == 'offline']
        for k in to_remove:
            del connected_pcs[k]
    return jsonify({'ok': True, 'removed': len(to_remove)})


# ──────────────────────────────────────────────
# 대시보드 HTML
# ──────────────────────────────────────────────
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>전원 중앙 제어 시스템</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Inter','Malgun Gothic',sans-serif;background:#0a0a1a;color:#e0e0e0;min-height:100vh;}

/* ── 헤더 ── */
.header{background:linear-gradient(135deg,#0f1128,#1a1145);padding:18px 28px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.06);}
.header-left h1{font-size:20px;font-weight:800;background:linear-gradient(90deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.header-left .server-ip{font-size:12px;color:#666;margin-top:2px;}
.stats{display:flex;gap:14px;}
.stat{text-align:center;padding:8px 16px;background:rgba(255,255,255,.04);border-radius:10px;min-width:70px;}
.stat .num{font-size:22px;font-weight:800;}
.stat .lbl{font-size:10px;color:#777;margin-top:1px;letter-spacing:.5px;}
.stat.online .num{color:#34d399;} .stat.offline .num{color:#f87171;}

/* ── 컨트롤 바 ── */
.controls{padding:14px 28px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;border-bottom:1px solid rgba(255,255,255,.04);}
.btn{padding:9px 18px;border:none;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;transition:all .15s;color:#fff;letter-spacing:.3px;}
.btn:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(0,0,0,.4);}
.btn:active{transform:translateY(0);}
.btn-danger{background:linear-gradient(135deg,#ef4444,#b91c1c);}
.btn-warning{background:linear-gradient(135deg,#f59e0b,#b45309);}
.btn-info{background:linear-gradient(135deg,#3b82f6,#1d4ed8);}
.btn-secondary{background:rgba(255,255,255,.08);color:#aaa;} .btn-secondary:hover{background:rgba(255,255,255,.12);}
.controls .sep{width:1px;height:28px;background:rgba(255,255,255,.08);margin:0 4px;}
.selected-info{font-size:12px;color:#888;margin-left:auto;}

/* ── PC 그리드 ── */
.pc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:12px;padding:20px 28px;}
.pc-card{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:14px 16px;transition:all .2s;cursor:pointer;position:relative;user-select:none;}
.pc-card:hover{background:rgba(255,255,255,.06);border-color:rgba(255,255,255,.12);transform:translateY(-2px);box-shadow:0 8px 25px rgba(0,0,0,.3);}
.pc-card.selected{border-color:#3b82f6;background:rgba(59,130,246,.08);box-shadow:0 0 0 1px #3b82f6;}
.pc-card.online{border-left:3px solid #34d399;}
.pc-card.offline{border-left:3px solid #ef4444;opacity:.5;}
.pc-card.offline:hover{opacity:.8;}

.status-row{display:flex;align-items:center;margin-bottom:6px;}
.dot{width:9px;height:9px;border-radius:50%;margin-right:7px;flex-shrink:0;}
.dot.online{background:#34d399;box-shadow:0 0 8px #34d39980;animation:pulse 2s infinite;}
.dot.offline{background:#ef4444;box-shadow:0 0 6px #ef444460;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.4;}}
.pc-name{font-weight:700;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.pc-ip{font-size:11px;color:#666;margin-top:2px;}
.pc-user{font-size:10px;color:#555;margin-top:1px;}
.pc-time{font-size:10px;color:#444;margin-top:3px;}
.pc-status-text{font-size:10px;font-weight:600;margin-top:4px;}
.pc-status-text.on{color:#34d399;} .pc-status-text.off{color:#ef4444;}

/* 선택 체크 */
.pc-check{position:absolute;top:8px;right:10px;width:18px;height:18px;border-radius:4px;border:2px solid rgba(255,255,255,.15);display:flex;align-items:center;justify-content:center;font-size:11px;transition:all .15s;}
.pc-card.selected .pc-check{background:#3b82f6;border-color:#3b82f6;color:#fff;}

/* ── 빈 상태 ── */
.empty{text-align:center;padding:80px 20px;color:#555;}
.empty .icon{font-size:48px;margin-bottom:16px;}
.empty .msg{font-size:15px;font-weight:600;}
.empty .sub{font-size:12px;color:#444;margin-top:6px;}

/* ── 모달 ── */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);backdrop-filter:blur(4px);z-index:100;align-items:center;justify-content:center;}
.modal-overlay.show{display:flex;}
.modal{background:#16162a;border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:24px;min-width:320px;max-width:400px;}
.modal h3{font-size:16px;margin-bottom:14px;font-weight:700;}
.modal p{font-size:13px;color:#999;margin-bottom:18px;line-height:1.5;}
.modal .btn-row{display:flex;gap:8px;justify-content:flex-end;}
.modal input[type=text]{width:100%;padding:8px 12px;border-radius:8px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.05);color:#eee;font-size:13px;margin-bottom:12px;outline:none;}
.modal input[type=text]:focus{border-color:#3b82f6;}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <h1>🖥️ 전원 중앙 제어 시스템</h1>
    <div class="server-ip">내부 접속: {{ server_ip }}:{{ server_port }}</div>
    {% if ngrok_url %}
    <div class="server-ip" style="color:#60a5fa; margin-top:5px; font-weight:600; cursor:pointer;" onclick="navigator.clipboard.writeText('{{ ngrok_url }}').then(()=>alert('외부 링크가 복사되었습니다!'))">외부 접속 링크: {{ ngrok_url }} (클릭하여 복사)</div>
    {% endif %}
  </div>
  <div class="stats">
    <div class="stat"><div class="num" id="stat-total">0</div><div class="lbl">전체</div></div>
    <div class="stat online"><div class="num" id="stat-online">0</div><div class="lbl">켜짐</div></div>
    <div class="stat offline"><div class="num" id="stat-offline">0</div><div class="lbl">꺼짐</div></div>
  </div>
</div>

<div class="controls">
  <button class="btn btn-danger" onclick="sendAll('shutdown')">⏻ 전체 종료</button>
  <button class="btn btn-warning" onclick="sendAll('sleep')">💤 전체 절전</button>
  <button class="btn btn-info" onclick="sendAll('restart')">🔄 전체 재부팅</button>
  <div class="sep"></div>
  <button class="btn btn-danger" onclick="sendSelected('shutdown')">⏻ 선택 종료</button>
  <button class="btn btn-warning" onclick="sendSelected('sleep')">💤 선택 절전</button>
  <button class="btn btn-info" onclick="sendSelected('restart')">🔄 선택 재부팅</button>
  <div class="sep"></div>
  <button class="btn btn-secondary" onclick="clearOffline()">🗑 오프라인 정리</button>
  <span class="selected-info" id="selected-info"></span>
</div>

<div class="pc-grid" id="pc-grid"></div>

<!-- 확인 모달 -->
<div class="modal-overlay" id="confirm-modal">
  <div class="modal">
    <h3 id="modal-title">확인</h3>
    <p id="modal-msg">정말 실행하시겠습니까?</p>
    <div class="btn-row">
      <button class="btn btn-secondary" onclick="closeModal()">취소</button>
      <button class="btn btn-danger" id="modal-ok" onclick="modalConfirm()">실행</button>
    </div>
  </div>
</div>

<script>
let pcs = [];
let selectedPcs = new Set();
let pendingAction = null;

// PC 목록 갱신
async function fetchPCs() {
    try {
        const res = await fetch('/api/pcs');
        pcs = await res.json();
        renderPCs();
        updateStats();
    } catch(e) {}
}

function renderPCs() {
    const grid = document.getElementById('pc-grid');
    if (pcs.length === 0) {
        grid.innerHTML = '<div class="empty"><div class="icon">📡</div><div class="msg">연결된 PC가 없습니다</div><div class="sub">학생 PC에서 스마트 전원 관리자가 실행되면 자동으로 표시됩니다</div></div>';
        return;
    }
    let html = '';
    for (const pc of pcs) {
        const isOnline = pc.status === 'online';
        const isSelected = selectedPcs.has(pc.pc_id);
        html += `<div class="pc-card ${isOnline?'online':'offline'} ${isSelected?'selected':''}" onclick="toggleSelect('${pc.pc_id}')">
            <div class="pc-check">${isSelected?'✓':''}</div>
            <div class="status-row">
                <span class="dot ${isOnline?'online':'offline'}"></span>
                <span class="pc-name">${pc.hostname || pc.pc_id}</span>
            </div>
            <div class="pc-ip">${pc.ip}</div>
            <div class="pc-user">${pc.user ? '👤 '+pc.user : ''}</div>
            <div class="pc-time">마지막 응답: ${pc.last_seen || '-'}</div>
            <div class="pc-status-text ${isOnline?'on':'off'}">${isOnline?'● 켜짐':'● 꺼짐'}</div>
        </div>`;
    }
    grid.innerHTML = html;
    document.getElementById('selected-info').textContent =
        selectedPcs.size > 0 ? `${selectedPcs.size}대 선택됨` : '';
}

function updateStats() {
    const total = pcs.length;
    const online = pcs.filter(p => p.status === 'online').length;
    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-online').textContent = online;
    document.getElementById('stat-offline').textContent = total - online;
}

function toggleSelect(pcId) {
    if (selectedPcs.has(pcId)) selectedPcs.delete(pcId);
    else selectedPcs.add(pcId);
    renderPCs();
}

// 명령 전송
function sendAll(action) {
    const labels = {shutdown:'전체 종료',sleep:'전체 절전',restart:'전체 재부팅'};
    showModal(`${labels[action]} 확인`, `정말 모든 PC를 ${labels[action]}하시겠습니까?`, () => {
        fetch('/api/send_command', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({target:'__ALL__', action})
        }).then(()=>{ closeModal(); });
    });
}

function sendSelected(action) {
    if (selectedPcs.size === 0) { alert('PC를 먼저 선택해주세요.'); return; }
    const labels = {shutdown:'종료',sleep:'절전',restart:'재부팅'};
    showModal(`선택 ${labels[action]} 확인`, `선택된 ${selectedPcs.size}대의 PC를 ${labels[action]}하시겠습니까?`, () => {
        for (const pcId of selectedPcs) {
            fetch('/api/send_command', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({target:pcId, action})
            });
        }
        selectedPcs.clear();
        closeModal();
        renderPCs();
    });
}

async function clearOffline() {
    await fetch('/api/clear_offline', {method:'POST'});
    fetchPCs();
}

// 모달
function showModal(title, msg, onOk) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-msg').textContent = msg;
    pendingAction = onOk;
    document.getElementById('confirm-modal').classList.add('show');
}
function closeModal() { document.getElementById('confirm-modal').classList.remove('show'); pendingAction=null; }
function modalConfirm() { if(pendingAction) pendingAction(); }

// 2초마다 갱신
setInterval(fetchPCs, 2000);
fetchPCs();
</script>
</body>
</html>"""


@app.route('/')
def dashboard():
    return render_template_string(
        DASHBOARD_HTML,
        server_ip=get_local_ip(),
        server_port=SERVER_PORT,
        ngrok_url=NGROK_URL
    )


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
if __name__ == '__main__':
    server_ip = get_local_ip()

    # Ngrok 실행 시도 (외부 접속용)
    try:
        from pyngrok import ngrok
        # ngrok을 통해 5000 포트를 외부에 노출
        public_url = ngrok.connect(f"127.0.0.1:{SERVER_PORT}")
        NGROK_URL = public_url.public_url
    except Exception as e:
        NGROK_URL = None
        print(f"Ngrok 실행 중 오류 발생 (무시됨): {e}")

    print(f"=" * 60)
    print(f"  [ 전원 중앙 제어 시스템 서버 ]")
    print(f"  내부망(학교/학원 내) 접속: http://{server_ip}:{SERVER_PORT}")
    if NGROK_URL:
        print(f"  [ 외부망(LTE/집 등) 접속 ]: {NGROK_URL}")
    else:
        print(f"  [ 외부 접속 설정 실패 ] (pyngrok 토큰이 없거나 네트워크 문제)")
    print(f"  브라우저에서 위 주소 중 하나로 접속하세요.")
    print(f"  UDP 자동 감지 포트: {BROADCAST_PORT}")
    print(f"=" * 60)

    # 백그라운드 스레드 시작
    threading.Thread(target=broadcast_thread, daemon=True).start()
    threading.Thread(target=cleanup_thread, daemon=True).start()

    # Flask 서버 시작 (모든 인터페이스에서 수신)
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=False, use_reloader=False)
