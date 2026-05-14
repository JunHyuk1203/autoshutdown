import os
import sys
import threading
import time
import json
import socket
import urllib.request
import urllib.error
import urllib.parse
import re
from datetime import datetime, timedelta

# Flask & P2P 
from flask import Flask, request, jsonify, render_template_string
import logging

# PyInstaller 환경 변수 오염(init.tcl) 방지 패치
# 업데이트 후 부모 프로세스의 환경변수가 상속되면 삭제된 임시 폴더를 참조하므로
# 항상 현재 _MEIPASS 기준으로 강제 재설정
if getattr(sys, 'frozen', False):
    # _MEIPASS2가 남아있으면 PyInstaller 부트로더가 혼동할 수 있으므로 제거
    os.environ.pop('_MEIPASS2', None)
    # 항상 현재 _MEIPASS 기준으로 TCL/TK 경로를 강제 설정 (기존 값 무시)
    _meipass = sys._MEIPASS.replace('\\', '/')
    os.environ['TCL_LIBRARY'] = _meipass + '/_tcl_data'
    os.environ['TK_LIBRARY'] = _meipass + '/_tk_data'

import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkfont
import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw
import ctypes
from ctypes import wintypes
import subprocess

CURRENT_VERSION = "1.1.29"

try:
    from pycaw.pycaw import AudioUtilities
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(application_path, "schedule_config.json")

DAYS = ["월", "화", "수", "목", "금", "토", "일"]
TIMETABLE = {
    "1교시 (08:40)": "08:40",
    "2교시 (09:40)": "09:40",
    "3교시 (10:40)": "10:40",
    "4교시 (11:40)": "11:40",
    "점심시간 (12:40)": "12:40",
    "5교시 (13:30)": "13:30",
    "6교시 (14:30)": "14:30",
    "7교시 (15:30)": "15:30",
    "방과후/기타 (16:30)": "16:30",
}

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('dwTime', wintypes.DWORD),
    ]

def get_idle_time():
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        tick = ctypes.windll.kernel32.GetTickCount()
        millis = (tick - lii.dwTime) & 0xFFFFFFFF
        return millis / 1000.0
    return 0.0

def is_media_playing():
    if not HAS_PYCAW: return False
    try:
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.State == 1: return True
    except Exception: pass
    return False

# ──────────────────────────────────────────────
# P2P Server Setup (Flask & UDP)
# ──────────────────────────────────────────────
app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

connected_pcs = {}
pending_commands = {}
data_lock = threading.Lock()
SERVER_PORT = 5000
BROADCAST_PORT = 5555
OFFLINE_THRESHOLD = 8
app_instance = None  # AutoShutdownAppV2 인스턴스 참조

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def send_udp_broadcast(msg_str):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg_str.encode('utf-8'), ('<broadcast>', BROADCAST_PORT))
        sock.close()
    except Exception:
        pass

@app.route('/api/pcs')
def get_pcs():
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
                'next_event': info.get('next_event', '-'),
            })
    return jsonify(pcs)

@app.route('/api/send_command', methods=['POST'])
def send_command():
    global app_instance
    data = request.get_json(force=True)
    target = data.get('target', '__ALL__')
    action = data.get('action', '')
    message = data.get('message', '')
    
    # 1. P2P (UDP)
    payload = json.dumps({
        'type': 'COMMAND',
        'target': target,
        'action': action,
        'message': message
    })
    send_udp_broadcast(payload)
    
    # 2. Local Central Server (Ngrok) - 큐에 명령 저장
    with data_lock:
        if target == '__ALL__':
            for pc in connected_pcs.keys():
                pending_commands[pc] = {'action': action, 'message': message}
        else:
            pending_commands[target] = {'action': action, 'message': message}
            
    # 3. Cloud P2P Forwarding - 내가 중앙 서버가 아닌 경우 중앙 서버로 전달
    if not data.get('forwarded'):
        url = app_instance.central_url_var.get().strip() if app_instance else ""
        if url:
            if not url.startswith("http"): url = "http://" + url
            def forward():
                try:
                    fdata = data.copy()
                    fdata['forwarded'] = True
                    req = urllib.request.Request(f"{url.rstrip('/')}/api/send_command", data=json.dumps(fdata).encode('utf-8'), method='POST', headers={'Content-Type': 'application/json'})
                    urllib.request.urlopen(req, timeout=3)
                except Exception:
                    pass
            threading.Thread(target=forward, daemon=True).start()
            
    return jsonify({'ok': True})

@app.route('/api/clear_offline', methods=['POST'])
def clear_offline():
    with data_lock:
        to_remove = [k for k, v in connected_pcs.items() if v.get('status') == 'offline']
        for k in to_remove:
            del connected_pcs[k]
    return jsonify({'ok': True})

@app.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    data = request.get_json(force=True)
    pc_id = data.get('pc_id')
    if not pc_id: return jsonify({'error': 'no pc_id'})
    with data_lock:
        connected_pcs[pc_id] = {
            'ip': data.get('ip', request.remote_addr),
            'hostname': data.get('hostname', pc_id),
            'user': data.get('user', ''),
            'status': data.get('status', 'online'),
            'next_event': data.get('next_event', '-'),
            'last_seen': datetime.now().strftime('%H:%M:%S'),
            'last_seen_ts': time.time()
        }
        cmd = pending_commands.pop(pc_id, None)
        pcs_copy = connected_pcs.copy()
    return jsonify({"status": "ok", "command": cmd, "pcs": pcs_copy})

@app.route('/api/config')
def get_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({})

@app.route('/api/config', methods=['POST'])
def update_config():
    global app_instance
    data = request.get_json(force=True)
    try:
        current = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                current = json.load(f)
                
        for k, v in data.items():
            if isinstance(v, dict) and k in current and isinstance(current[k], dict):
                current[k].update(v)
            else:
                current[k] = v
                
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(current, f, ensure_ascii=False, indent=4)
        if app_instance:
            app_instance.root.after(0, lambda d=data: app_instance.reload_config_from_web(d))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pc_config/<pc_id>')
def get_pc_config(pc_id):
    with data_lock:
        pc = connected_pcs.get(pc_id)
    if not pc:
        return jsonify({'error': 'PC not found'}), 404
    ip = pc.get('ip', '')
    try:
        url = f'http://{ip}:{SERVER_PORT}/api/config'
        req = urllib.request.Request(url, headers={'User-Agent': 'SmartPower/1.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return jsonify(json.loads(resp.read().decode()))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pc_config/<pc_id>', methods=['POST'])
def set_pc_config(pc_id):
    with data_lock:
        pc = connected_pcs.get(pc_id)
    if not pc:
        return jsonify({'error': 'PC not found'}), 404
    ip = pc.get('ip', '')
    data = request.get_json(force=True)
    try:
        url = f'http://{ip}:{SERVER_PORT}/api/config'
        payload = json.dumps(data).encode()
        req = urllib.request.Request(url, data=payload, method='POST',
                                     headers={'Content-Type': 'application/json', 'User-Agent': 'SmartPower/1.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return jsonify(json.loads(resp.read().decode()))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search_school', methods=['GET'])
def search_school_api():
    q = request.args.get('q', '')
    url = f"https://open.neis.go.kr/hub/schoolInfo?Type=json&pIndex=1&pSize=20&SCHUL_NM={urllib.parse.quote(q)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            return jsonify(json.loads(res.read().decode('utf-8')))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
.header{background:linear-gradient(135deg,#0f1128,#1a1145);padding:18px 28px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.06);}
.header-left h1{font-size:20px;font-weight:800;background:linear-gradient(90deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.header-left .server-ip{font-size:12px;color:#666;margin-top:2px;}
.stats{display:flex;gap:14px;}
.stat{text-align:center;padding:8px 16px;background:rgba(255,255,255,.04);border-radius:10px;min-width:70px;}
.stat .num{font-size:22px;font-weight:800;}
.stat .lbl{font-size:10px;color:#777;margin-top:1px;letter-spacing:.5px;}
.stat.online .num{color:#34d399;} .stat.offline .num{color:#f87171;}
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
.pc-next{font-size:11px;color:#a78bfa;margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,.04);font-weight:600;}
.pc-check{position:absolute;top:8px;left:10px;width:18px;height:18px;border-radius:4px;border:2px solid rgba(255,255,255,.15);display:flex;align-items:center;justify-content:center;font-size:11px;transition:all .15s;}
.pc-card.selected .pc-check{background:#3b82f6;border-color:#3b82f6;color:#fff;}
.empty{text-align:center;padding:80px 20px;color:#555;}
.empty .icon{font-size:48px;margin-bottom:16px;}
.empty .msg{font-size:15px;font-weight:600;}
.empty .sub{font-size:12px;color:#444;margin-top:6px;}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);backdrop-filter:blur(4px);z-index:100;align-items:center;justify-content:center;}
.modal-overlay.show{display:flex;}
.modal{background:#16162a;border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:24px;min-width:320px;max-width:400px;}
.modal h3{font-size:16px;margin-bottom:14px;font-weight:700;}
.modal p{font-size:13px;color:#999;margin-bottom:18px;line-height:1.5;}
.modal .btn-row{display:flex;gap:8px;justify-content:flex-end;}
.modal input[type=text]{width:100%;padding:8px 12px;border-radius:8px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.05);color:#eee;font-size:13px;margin-bottom:12px;outline:none;}
.modal input[type=text]:focus{border-color:#3b82f6;}
/* PC 별 설정 모달 */
.pc-modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(6px);z-index:200;align-items:center;justify-content:center;}
.pc-modal-overlay.show{display:flex;}
.pc-modal{background:#16162a;border:1px solid rgba(255,255,255,.12);border-radius:18px;padding:24px;width:min(700px,95vw);max-height:90vh;overflow-y:auto;}
.pc-modal h2{font-size:16px;font-weight:800;margin-bottom:16px;background:linear-gradient(90deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.pc-section{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:14px;margin-bottom:12px;}
.pc-section h4{font-size:12px;font-weight:700;color:#a78bfa;margin-bottom:10px;}
.pc-row{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;}
.pc-row label{font-size:11px;color:#aaa;min-width:110px;}
.pc-row input[type=text],.pc-row input[type=number],.pc-row select{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);border-radius:6px;color:#eee;padding:5px 9px;font-size:12px;outline:none;}
.pc-row input[type=text]{flex:1;min-width:140px;}
.pc-sched{width:100%;border-collapse:collapse;font-size:10px;}
.pc-sched th{background:rgba(255,255,255,.05);padding:4px;text-align:center;color:#888;}
.pc-sched td{padding:3px;text-align:center;border-bottom:1px solid rgba(255,255,255,.03);}
.pc-sched select{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:4px;color:#ccc;padding:1px;font-size:9px;}
.pc-gear-btn{position:absolute;top:8px;right:8px;background:rgba(255,255,255,.08);border:none;border-radius:6px;color:#aaa;padding:3px 7px;cursor:pointer;font-size:13px;z-index:2;}
.pc-gear-btn:hover{background:rgba(167,139,250,.25);color:#a78bfa;}
/* 설정 패널 */
.settings-panel{display:none;padding:20px 28px;border-top:1px solid rgba(255,255,255,.06);}
.settings-panel.open{display:block;}
.settings-section{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:16px;margin-bottom:14px;}
.settings-section h3{font-size:13px;font-weight:700;margin-bottom:12px;color:#a78bfa;}
.settings-row{display:flex;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap;}
.settings-row label{font-size:12px;color:#aaa;min-width:120px;}
.settings-row input[type=number],.settings-row select{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);border-radius:6px;color:#eee;padding:5px 10px;font-size:12px;}
.toggle-sw{position:relative;width:36px;height:20px;flex-shrink:0;}
.toggle-sw input{opacity:0;width:0;height:0;}
.toggle-slider{position:absolute;inset:0;background:#444;border-radius:20px;cursor:pointer;transition:.2s;}
.toggle-slider:before{content:'';position:absolute;width:14px;height:14px;left:3px;top:3px;background:#fff;border-radius:50%;transition:.2s;}
.toggle-sw input:checked+.toggle-slider{background:#3b82f6;}
.toggle-sw input:checked+.toggle-slider:before{transform:translateX(16px);}
.schedule-table{width:100%;border-collapse:collapse;font-size:11px;}
.schedule-table th{background:rgba(255,255,255,.05);padding:5px 4px;text-align:center;font-weight:600;color:#888;}
.schedule-table td{padding:3px 4px;text-align:center;border-bottom:1px solid rgba(255,255,255,.04);}
.schedule-table select{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:4px;color:#ccc;padding:2px;font-size:10px;}
.btn-success{background:linear-gradient(135deg,#10b981,#059669);}
.save-toast{position:fixed;bottom:24px;right:24px;background:#10b981;color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:700;display:none;z-index:200;}
</style>
</head>
<body>
<div class="header">
  <div class="header-left">
    <h1>🖥️ 전원 중앙 제어 시스템 (P2P)</h1>
    <div class="server-ip">내부 접속: {{ server_ip }}:{{ server_port }}</div>
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
  <div class="sep"></div>
  <button class="btn btn-secondary" id="settings-toggle-btn" onclick="toggleSettings()">⚙️ 설정</button>
  <span class="selected-info" id="selected-info"></span>
</div>

<div class="pc-grid" id="pc-grid"></div>

<!-- 설정 패널 -->
<div class="settings-panel" id="settings-panel">
  <div class="settings-section">
    <h3>🔔 일반 설정</h3>
    <div class="settings-row">
      <label>오늘 하루 작동 끄기</label>
      <label class="toggle-sw"><input type="checkbox" id="cfg-skip-today"><span class="toggle-slider"></span></label>
    </div>
    <div class="settings-row">
      <label>화면 팝업 알림 표시</label>
      <label class="toggle-sw"><input type="checkbox" id="cfg-popup"><span class="toggle-slider"></span></label>
    </div>
    <div class="settings-row">
      <label>시작프로그램 등록</label>
      <label class="toggle-sw"><input type="checkbox" id="cfg-autostart"><span class="toggle-slider"></span></label>
    </div>
    <div class="settings-row">
      <label>실행 N분 전</label>
      <input type="number" id="cfg-minutes" min="0" max="120" style="width:70px">
      <span style="font-size:12px;color:#888">분</span>
    </div>
  </div>
  <div class="settings-section">
    <h3>📅 주간 스케줄</h3>
    <div style="overflow-x:auto">
    <table class="schedule-table">
      <thead><tr><th>시간</th><th>월</th><th>화</th><th>수</th><th>목</th><th>금</th><th>토</th><th>일</th></tr></thead>
      <tbody id="schedule-tbody"></tbody>
    </table>
    </div>
  </div>
</div>

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

<!-- PC 별 설정 모달 -->
<div class="pc-modal-overlay" id="pc-settings-overlay">
  <div class="pc-modal">
    <h2 id="pc-modal-title">⚙️ PC 설정</h2>
    <div class="pc-section">
      <h4>📚 학교 / NEIS 설정</h4>
      <div class="pc-row"><label>NEIS API 키</label><input type="text" id="pm-api-key" placeholder="인증키 입력"></div>
      <div class="pc-row"><label>학교명</label><input type="text" id="pm-school-name" placeholder="예: 서울초등학교" readonly style="background:rgba(255,255,255,.03);flex:1;"><button class="btn btn-secondary" onclick="openSchoolSearch()" style="padding:4px 8px;font-size:11px;margin-left:4px;">검색</button></div>
      <input type="hidden" id="pm-school-code">
      <input type="hidden" id="pm-office-code">
      <input type="hidden" id="pm-school-kind">
      <div class="pc-row"><label>학년</label><input type="number" id="pm-grade" min="1" max="6" style="width:60px"></div>
      <div class="pc-row"><label>반</label><input type="number" id="pm-class" min="1" max="20" style="width:60px"></div>
    </div>
    <div class="pc-section">
      <h4>🔔 일반 설정</h4>
      <div class="pc-row"><label>오늘 하루 기</label><label class="toggle-sw"><input type="checkbox" id="pm-skip"><span class="toggle-slider"></span></label></div>
      <div class="pc-row"><label>팝업 알림</label><label class="toggle-sw"><input type="checkbox" id="pm-popup"><span class="toggle-slider"></span></label></div>
      <div class="pc-row"><label>시작프로그램</label><label class="toggle-sw"><input type="checkbox" id="pm-autostart"><span class="toggle-slider"></span></label></div>
      <div class="pc-row"><label>N분 전 실행</label><input type="number" id="pm-minutes" min="0" max="120" style="width:60px"> <span style="font-size:11px;color:#888">분</span></div>
    </div>
    <div class="pc-section">
      <h4>📅 주간 스케줄</h4>
      <div style="overflow-x:auto"><table class="pc-sched"><thead><tr><th>시간</th><th>월</th><th>화</th><th>수</th><th>목</th><th>금</th><th>토</th><th>일</th></tr></thead><tbody id="pm-sched-tbody"></tbody></table></div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:8px">
      <button class="btn btn-secondary" onclick="closePcSettings()">&#x2715; 닫기</button>
      <button class="btn btn-success" onclick="savePcSettings()">💾 저장</button>
    </div>
  </div>
</div>

<!-- 학교 검색 모달 -->
<div class="pc-modal-overlay" id="school-search-overlay" style="z-index: 300;">
  <div class="pc-modal" style="width: 400px; max-width: 90vw;">
    <h2 style="font-size:15px; margin-bottom:12px;">🔍 학교 검색</h2>
    <div style="display:flex; gap:8px; margin-bottom:12px;">
      <input type="text" id="school-search-input" placeholder="학교명 입력 (예: 서울과학고)" style="flex:1; padding:8px; border-radius:6px; border:1px solid rgba(255,255,255,.1); background:rgba(255,255,255,.05); color:#fff; font-size:12px;" onkeypress="if(event.key==='Enter') doSchoolSearch()">
      <button class="btn btn-info" onclick="doSchoolSearch()" style="padding:8px 14px;">검색</button>
    </div>
    <div id="school-search-results" style="max-height: 250px; overflow-y: auto; margin-bottom:12px; font-size:12px;"></div>
    <div style="text-align:right;">
      <button class="btn btn-secondary" onclick="closeSchoolSearch()">닫기</button>
    </div>
  </div>
</div>

<script>
let pcs = [];
let selectedPcs = new Set();
let pendingAction = null;

async function fetchPCs() {
    try {
        const res = await fetch('/api/pcs?t=' + new Date().getTime());
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
        const gearBtn = isOnline 
            ? `<button class="pc-gear-btn" onclick="openPcSettings('${pc.pc_id}','${pc.hostname||pc.pc_id}');event.stopPropagation()">⚙️</button>`
            : `<button class="pc-gear-btn" style="opacity:0.4;cursor:not-allowed;" onclick="alert('오프라인 상태의 PC는 설정에 접근할 수 없습니다. (동기화 불가)');event.stopPropagation()">⚙️</button>`;

        html += `<div class="pc-card ${isOnline?'online':'offline'} ${isSelected?'selected':''}" onclick="toggleSelect('${pc.pc_id}')" style="position:relative">
            ${gearBtn}
            <div class="pc-check">${isSelected?'✓':''}</div>
            <div class="status-row">
                <span class="dot ${isOnline?'online':'offline'}"></span>
                <span class="pc-name">${pc.hostname || pc.pc_id}</span>
            </div>
            <div class="pc-ip">${pc.ip}</div>
            <div class="pc-user">${pc.user ? '👤 '+pc.user : ''}</div>
            <div class="pc-time">마지막 응답: ${pc.last_seen || '-'}</div>
            <div class="pc-status-text ${isOnline?'on':'off'}">${isOnline?'● 켜짐':'● 꺼짐'}</div>
            <div class="pc-next">${isOnline ? '⏰ 다음: ' + (pc.next_event || '-') : '오프라인'}</div>
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

function showModal(title, msg, onOk) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-msg').textContent = msg;
    pendingAction = onOk;
    document.getElementById('confirm-modal').classList.add('show');
}
function closeModal() { document.getElementById('confirm-modal').classList.remove('show'); pendingAction=null; }
function modalConfirm() { if(pendingAction) pendingAction(); }

setInterval(fetchPCs, 2000);
fetchPCs();

// 설정 패널
const DAYS=['\uc6d4','\ud654','\uc218','\ubaa9','\uae08','\ud1a0','\uc77c'];
const SLOTS=['1\uad50\uc2dc (08:40)','2\uad50\uc2dc (09:40)','3\uad50\uc2dc (10:40)','4\uad50\uc2dc (11:40)','\uc810\uc2ec\uc2dc\uac04 (12:40)','5\uad50\uc2dc (13:30)','6\uad50\uc2dc (14:30)','7\uad50\uc2dc (15:30)','\ubc29\uacfc\ud6c4/\uae30\ud0c0 (16:30)'];
let cfgData = {};

function toggleSettings(){
    const p=document.getElementById('settings-panel');
    const btn=document.getElementById('settings-toggle-btn');
    p.classList.toggle('open');
    if(p.classList.contains('open')){
        btn.style.background='rgba(167,139,250,.3)';
        loadSettings();
    } else {
        btn.style.background='';
    }
}

async function loadSettings(){
    try{
        const res=await fetch('/api/config');
        cfgData=await res.json();
        const today=new Date().toISOString().slice(0,10);
        document.getElementById('cfg-skip-today').checked=(cfgData.skip_date===today);
        document.getElementById('cfg-popup').checked=cfgData.show_popup_alert!==false;
        document.getElementById('cfg-autostart').checked=!!cfgData.autostart;
        document.getElementById('cfg-minutes').value=cfgData.minutes_before||2;
        // 개별 즉시 저장 핸들러
        document.getElementById('cfg-skip-today').onchange=function(){savePartial({skip_date:this.checked?new Date().toISOString().slice(0,10):''});}
        document.getElementById('cfg-popup').onchange=function(){savePartial({show_popup_alert:this.checked});}
        document.getElementById('cfg-autostart').onchange=function(){savePartial({autostart:this.checked});}
        document.getElementById('cfg-minutes').onchange=function(){savePartial({minutes_before:parseInt(this.value)||2});}
        buildScheduleTable();
    }catch(e){}
}

function buildScheduleTable(){
    const tbody=document.getElementById('schedule-tbody');
    let html='';
    for(const slot of SLOTS){
        html+=`<tr><td style="font-size:10px;color:#aaa;white-space:nowrap;padding-right:8px">${slot.replace(/ \(.+\)/,'')}</td>`;
        for(const day of DAYS){
            const val=cfgData[day]?cfgData[day][slot]:null;
            const en=val?val.enabled:false;
            const ac=val?val.action:'\uc2dc\uc2a4\ud15c \uc885\ub8cc';
            const shut=ac==='\uc2dc\uc2a4\ud15c \uc885\ub8cc'?'selected':'';
            const slp=ac==='\uc808\uc804 \ubaa8\ub4dc'?'selected':'';
            html+=`<td><input type="checkbox" data-day="${day}" data-slot="${slot}" class="sch-chk" ${en?'checked':''}><br><select data-day="${day}" data-slot="${slot}" class="sch-act" style="display:${en?'':'none'}"><option ${shut}>\uc885\ub8cc</option><option value="\uc808\uc804 \ubaa8\ub4dc" ${slp}>\uc808\uc804</option></select></td>`;
        }
        html+='</tr>';
    }
    tbody.innerHTML=html;
    // 체크박스: 즈시 저장
    document.querySelectorAll('.sch-chk').forEach(chk=>{
        chk.addEventListener('change',function(){
            const day=this.dataset.day, slot=this.dataset.slot;
            const sel=tbody.querySelector(`select[data-day="${day}"][data-slot="${slot}"]`);
            if(sel) sel.style.display=this.checked?'':'none';
            const action=sel&&this.checked?(sel.value||'\uc2dc\uc2a4\ud15c \uc885\ub8cc'):'\uc2dc\uc2a4\ud15c \uc885\ub8cc';
            const patch={}; patch[day]={}; patch[day][slot]={enabled:this.checked,action};
            savePartial(patch);
        });
    });
    // 드롭다운: 즈시 저장
    document.querySelectorAll('.sch-act').forEach(sel=>{
        sel.addEventListener('change',function(){
            const day=this.dataset.day, slot=this.dataset.slot;
            const patch={}; patch[day]={}; patch[day][slot]={enabled:true,action:this.value||'\uc2dc\uc2a4\ud15c \uc885\ub8cc'};
            savePartial(patch);
        });
    });
}

async function savePartial(patch){
    try{
        await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(patch)});
        showToast();
    }catch(e){}
}

function showToast(){
    const t=document.querySelector('.save-toast');
    t.style.display='block';
    clearTimeout(t._tid);
    t._tid=setTimeout(()=>t.style.display='none',1500);
}

let currentPcId = null;
let currentPcCfg = {};

async function openPcSettings(pcId, hostname) {
    const pc = pcs.find(p => p.pc_id === pcId);
    if (pc && pc.status !== 'online') {
        alert('오프라인 상태의 PC는 설정에 접근할 수 없습니다. (동기화 불가)');
        return;
    }
    currentPcId = pcId;
    document.getElementById('pc-modal-title').textContent = `⚙️ ${hostname} 설정`;
    document.getElementById('pc-settings-overlay').classList.add('show');
    
    // 자동 저장 바인딩
    const inputs = ['pm-api-key', 'pm-school-code', 'pm-office-code', 'pm-school-kind', 'pm-grade', 'pm-class', 'pm-minutes'];
    inputs.forEach(id => { document.getElementById(id).onchange = () => savePcSettings(); });
    ['pm-popup', 'pm-autostart', 'pm-skip'].forEach(id => { document.getElementById(id).onchange = () => savePcSettings(); });

    try {
        const res = await fetch(`/api/pc_config/${pcId}`);
        const data = await res.json();
        currentPcCfg = data;
        
        const info = data.school_info || {};
        document.getElementById('pm-api-key').value = info.api_key || '';
        document.getElementById('pm-school-name').value = info.name || info.school_name || '';
        document.getElementById('pm-school-code').value = info.school_code || '';
        document.getElementById('pm-office-code').value = info.office_code || '';
        document.getElementById('pm-school-kind').value = info.school_kind || '';
        document.getElementById('pm-grade').value = info.grade || '';
        document.getElementById('pm-class').value = info.class_nm || '';
        
        document.getElementById('pm-popup').checked = data.show_popup_alert !== false;
        document.getElementById('pm-autostart').checked = !!data.autostart;
        document.getElementById('pm-minutes').value = data.minutes_before || 2;
        const today = new Date().toISOString().slice(0,10);
        document.getElementById('pm-skip').checked = (data.skip_date === today);
        
        buildPcScheduleTable();
    } catch(e) {
        alert('설정을 불러오는데 실패했습니다: ' + e);
        closePcSettings();
    }
}

function closePcSettings() {
    document.getElementById('pc-settings-overlay').classList.remove('show');
    currentPcId = null;
}

function buildPcScheduleTable() {
    const tbody = document.getElementById('pm-sched-tbody');
    let html = '';
    for(const slot of SLOTS) {
        html += `<tr><td style="white-space:nowrap">${slot.replace(/ \(.+\)/,'')}</td>`;
        for(const day of DAYS) {
            const val = currentPcCfg[day] ? currentPcCfg[day][slot] : null;
            const en = val ? val.enabled : false;
            const ac = val ? val.action : '시스템 종료';
            const shut = ac === '시스템 종료' ? 'selected' : '';
            const slp = ac === '절전 모드' ? 'selected' : '';
            html += `<td><input type="checkbox" data-day="${day}" data-slot="${slot}" class="pm-chk" ${en?'checked':''}><br><select data-day="${day}" data-slot="${slot}" class="pm-act" style="display:${en?'':'none'}"><option ${shut}>종료</option><option value="절전 모드" ${slp}>절전</option></select></td>`;
        }
        html += '</tr>';
    }
    tbody.innerHTML = html;
    tbody.querySelectorAll('.pm-chk, .pm-act').forEach(el => {
        el.onchange = function() {
            if(this.classList.contains('pm-chk')) {
                const sel = tbody.querySelector(`select[data-day="${this.dataset.day}"][data-slot="${this.dataset.slot}"]`);
                if(sel) sel.style.display = this.checked ? '' : 'none';
            }
            savePcSettings();
        };
    });
}

async function savePcSettings() {
    if(!currentPcId) return;
    const today = new Date().toISOString().slice(0,10);
    const payload = {
        school_info: {
            api_key: document.getElementById('pm-api-key').value,
            name: document.getElementById('pm-school-name').value,
            school_code: document.getElementById('pm-school-code').value,
            office_code: document.getElementById('pm-office-code').value,
            school_kind: document.getElementById('pm-school-kind').value,
            grade: document.getElementById('pm-grade').value,
            class_nm: document.getElementById('pm-class').value
        },
        show_popup_alert: document.getElementById('pm-popup').checked,
        autostart: document.getElementById('pm-autostart').checked,
        minutes_before: parseInt(document.getElementById('pm-minutes').value) || 2,
        skip_date: document.getElementById('pm-skip').checked ? today : ''
    };
    
    for(const day of DAYS) { payload[day] = {}; }
    document.querySelectorAll('.pm-chk').forEach(chk => {
        const day = chk.dataset.day, slot = chk.dataset.slot;
        const sel = document.querySelector(`.pm-act[data-day="${day}"][data-slot="${slot}"]`);
        const action = sel ? sel.value || '시스템 종료' : '시스템 종료';
        payload[day][slot] = { enabled: chk.checked, action: chk.checked ? action : '시스템 종료' };
    });
    
    try {
        const res = await fetch(`/api/pc_config/${currentPcId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if(result.error) throw new Error(result.error);
        showToast();
        setTimeout(fetchPCs, 500);
    } catch(e) {
        console.error('저장 실패:', e);
    }
}

function openSchoolSearch() {
    document.getElementById('school-search-input').value = '';
    document.getElementById('school-search-results').innerHTML = '';
    document.getElementById('school-search-overlay').classList.add('show');
    document.getElementById('school-search-input').focus();
}

function closeSchoolSearch() {
    document.getElementById('school-search-overlay').classList.remove('show');
}

async function doSchoolSearch() {
    const q = document.getElementById('school-search-input').value.trim();
    if(!q) return;
    const resDiv = document.getElementById('school-search-results');
    resDiv.innerHTML = '<div style="text-align:center;color:#888;padding:10px;">검색 중...</div>';
    try {
        const res = await fetch(`/api/search_school?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        resDiv.innerHTML = '';
        if(data.schoolInfo) {
            const rows = data.schoolInfo[1].row;
            rows.forEach(r => {
                const div = document.createElement('div');
                div.style.padding = '10px';
                div.style.borderBottom = '1px solid rgba(255,255,255,.05)';
                div.style.cursor = 'pointer';
                div.innerHTML = `<strong style="color:#a78bfa;">${r.SCHUL_NM}</strong><br><span style="font-size:10px;color:#aaa;">${r.ORG_RDNMA}</span>`;
                div.onclick = () => {
                    document.getElementById('pm-school-name').value = r.SCHUL_NM;
                    document.getElementById('pm-school-code').value = r.SD_SCHUL_CODE;
                    document.getElementById('pm-office-code').value = r.ATPT_OFCDC_SC_CODE;
                    document.getElementById('pm-school-kind').value = r.SCHUL_KND_SC_NM;
                    closeSchoolSearch();
                    savePcSettings();
                };
                div.onmouseover = () => div.style.background = 'rgba(255,255,255,.05)';
                div.onmouseout = () => div.style.background = 'transparent';
                resDiv.appendChild(div);
            });
        } else {
            resDiv.innerHTML = '<div style="text-align:center;color:#888;padding:10px;">검색 결과가 없습니다.</div>';
        }
    } catch(e) {
        resDiv.innerHTML = `<div style="text-align:center;color:#ef4444;padding:10px;">오류 발생: ${e}</div>`;
    }
}
</script>
<div class="save-toast">✅ 설정이 저장되었습니다</div>
</body>
</html>"""

@app.route('/')
def dashboard():
    return render_template_string(
        DASHBOARD_HTML,
        server_ip=get_local_ip(),
        server_port=SERVER_PORT
    )

def is_media_playing():
    if not HAS_PYCAW: return False
    try:
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.State == 1: return True
    except Exception: pass
    return False

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class AutoShutdownAppV2:
    def __init__(self, root):
        self.root = root
        
        self._just_updated = "--just-updated" in sys.argv
        
        # 이전 업데이트에서 남겨진 임시 파일들 삭제 시도
        def _cleanup_old_files():
            try:
                current_exe = sys.executable if getattr(sys, 'frozen', False) else None
                if current_exe:
                    old_exe = current_exe + ".old"
                    if os.path.exists(old_exe):
                        try:
                            os.remove(old_exe)
                        except PermissionError:
                            # 프로세스가 아직 덜 닫혀 잠겨있을 수 있으므로 1초 뒤 재시도
                            self.root.after(1000, _cleanup_old_files)
                            return
                    launcher_vbs = os.path.join(os.path.dirname(current_exe), "_update_launcher.vbs")
                    if os.path.exists(launcher_vbs):
                        os.remove(launcher_vbs)
                    launcher_bat = os.path.join(os.path.dirname(current_exe), "_update_launcher.bat")
                    if os.path.exists(launcher_bat):
                        os.remove(launcher_bat)
            except: pass
            
        _cleanup_old_files()
        
        available_fonts = tkfont.families(root=self.root)
        self.font_family = "Malgun Gothic"
        for f in ["Pretendard Variable", "Pretendard", "Noto Sans KR", "NanumSquareNeo", "NanumSquare", "NanumGothic", "나눔스퀘어", "나눔고딕", "Malgun Gothic"]:
            if f in available_fonts:
                self.font_family = f
                break
                
        self.root.title(f"스마트 전원 관리자 (v{CURRENT_VERSION})")
        self.root.geometry("340x460")
        self.root.resizable(False, False)
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        self.skipped_events = set()
        self.config = self.load_config()
        self.vars = {day: {} for day in DAYS}
        self.subject_labels = {day: {} for day in DAYS}
        
        self.school_info = self.config.get("school_info", {})
        self.timetable_cache = self.config.get("timetable_cache", {})
        self.meal_cache = self.config.get("meal_cache", {})
        
        self.show_popup_var = ctk.BooleanVar(value=self.config.get("show_popup_alert", True))
        self.autostart_var = ctk.BooleanVar(value=self.config.get("autostart", False))
        self.minutes_var = ctk.StringVar(value=str(self.config.get("minutes_before", 2)))
        self.skip_today_var = ctk.BooleanVar(value=(self.config.get("skip_date") == datetime.now().strftime("%Y-%m-%d")))
        url_val = self.config.get("central_server_url", "")
        if not url_val: url_val = "https://crudely-feast-colt.ngrok-free.dev"
        self.central_url_var = ctk.StringVar(value=url_val)
        
        token_val = self.config.get("ngrok_token", "")
        if not token_val: token_val = "3DZmg3sqJ6RKsm06VYzURXc3TVG_3PRerzUhuj9BiVuEohBit"
        self.ngrok_token_var = ctk.StringVar(value=token_val)
        
        domain_val = self.config.get("ngrok_domain", "")
        if not domain_val: domain_val = "crudely-feast-colt.ngrok-free.dev"
        self.ngrok_domain_var = ctk.StringVar(value=domain_val)
        self.ngrok_url_var = ctk.StringVar()
        
        self.is_server_var = ctk.BooleanVar(value=self.config.get("is_server", False))
        
        for day in DAYS:
            for class_name in TIMETABLE.keys():
                class_config = self.config.get(day, {}).get(class_name, {})
                if isinstance(class_config, bool):
                    is_enabled = class_config
                    action_val = "시스템 종료"
                else:
                    is_enabled = class_config.get("enabled", False)
                    action_val = class_config.get("action", "시스템 종료")
                    
                self.vars[day][class_name] = {
                    "enabled": ctk.BooleanVar(value=is_enabled),
                    "action": ctk.StringVar(value=action_val)
                }
                self.vars[day][class_name]["enabled"].trace_add('write', self.save_config_callback)
                self.vars[day][class_name]["action"].trace_add('write', self.save_config_callback)
                
        self.show_popup_var.trace_add('write', self.save_config_callback)
        self.autostart_var.trace_add('write', self.save_config_callback)
        self.minutes_var.trace_add('write', self.save_config_callback)
        
        self.dash_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.dash_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        title_lbl = ctk.CTkLabel(self.dash_frame, text=f"스마트 전원 관리자 (v{CURRENT_VERSION})", font=ctk.CTkFont(family=self.font_family, size=16, weight="bold"))
        title_lbl.pack(pady=(0, 5))
        
        local_ip = get_local_ip()
        remote_url = f"http://{local_ip}:{SERVER_PORT}"
        
        def open_url(e):
            import webbrowser
            webbrowser.open(remote_url)
            
        url_lbl = ctk.CTkLabel(self.dash_frame, text=f"🌐 원격 제어: {remote_url}", font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"), text_color="#3498DB", cursor="hand2")
        url_lbl.pack(pady=(0, 10))
        url_lbl.bind("<Button-1>", open_url)
        
        status_card = ctk.CTkFrame(self.dash_frame, fg_color=("gray95", "gray15"), corner_radius=15)
        status_card.pack(fill="x", pady=5, ipady=15)
        
        self.countdown_var = ctk.StringVar(value="상태를 점검 중입니다...")
        self.countdown_label = ctk.CTkLabel(status_card, textvariable=self.countdown_var, font=ctk.CTkFont(family=self.font_family, size=14, weight="bold"), text_color="#1F6AA5")
        self.countdown_label.pack(pady=(15, 5))
        
        self.status_detail_var = ctk.StringVar(value="대기 중...")
        ctk.CTkLabel(status_card, textvariable=self.status_detail_var, font=ctk.CTkFont(family=self.font_family, size=11), text_color="gray").pack()
        
        self.timetable_label = ctk.CTkLabel(status_card, text="", font=ctk.CTkFont(family=self.font_family, size=10), text_color="#27AE60", wraplength=280)
        self.timetable_label.pack(pady=(5, 0))
        
        self.meal_label = ctk.CTkLabel(status_card, text="", font=ctk.CTkFont(family=self.font_family, size=10), text_color="#E67E22", wraplength=300, justify="left")
        self.meal_label.pack(pady=(2, 5))
        
        action_frame = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        action_frame.pack(fill="x", pady=15)
        
        skip_today_chk = ctk.CTkSwitch(action_frame, text="오늘 하루 작동 끄기", variable=self.skip_today_var, font=ctk.CTkFont(family=self.font_family, size=12, weight="bold"), command=self.toggle_skip_today_dashboard)
        skip_today_chk.pack(anchor="w", pady=5, padx=10)
        
        skip_next_btn = ctk.CTkButton(action_frame, text="이번 스케줄 건너뛰기 ⏭️", command=self.skip_next_schedule, font=ctk.CTkFont(family=self.font_family, size=12, weight="bold"), fg_color="#E67E22", hover_color="#D35400", height=32)
        skip_next_btn.pack(fill="x", pady=5, padx=10)
        
        bottom_frame = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", pady=(10, 0))
        
        settings_btn = ctk.CTkButton(bottom_frame, text="⚙️ 상세 설정", command=self.open_settings_window, font=ctk.CTkFont(family=self.font_family, size=13), width=130, height=35)
        settings_btn.pack(side="left")
        
        hide_btn = ctk.CTkButton(bottom_frame, text="창 숨기기", command=self.hide_window, font=ctk.CTkFont(family=self.font_family, size=13), width=130, height=35, fg_color=("gray75", "gray30"), text_color=("black", "white"), hover_color=("gray65", "gray20"))
        hide_btn.pack(side="right")
        
        self.is_running = True
        self.icon = None
        self.last_triggered_time = None
        self.pending_shutdown = False
        self.pending_shutdown_target = None
        self.pending_action = "시스템 종료"
        self.last_media_time = 0
        
        global app_instance
        app_instance = self
        
        threading.Thread(target=self.monitor_time, daemon=True).start()
        threading.Thread(target=self.check_for_updates, daemon=True).start()
        threading.Thread(target=self.p2p_listener_thread, daemon=True).start()
        threading.Thread(target=self.p2p_broadcaster_thread, daemon=True).start()
        threading.Thread(target=self.flask_server_thread, daemon=True).start()
        threading.Thread(target=self.http_poller_thread, daemon=True).start()
        
        if self.is_server_var.get():
            threading.Thread(target=self.start_ngrok_background, daemon=True).start()
            
        today = datetime.today()
        monday_str = (today - timedelta(days=today.weekday())).strftime("%Y%m%d")
        if self.school_info and monday_str not in self.timetable_cache:
            threading.Thread(target=self.update_timetable_background, daemon=True).start()
        else:
            self.root.after(0, self.update_timetable_ui)
        
    def start_ngrok_background(self):
        try:
            import subprocess
            original_popen = subprocess.Popen
            
            def patched_popen(*args, **kwargs):
                if 'startupinfo' not in kwargs:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    kwargs['startupinfo'] = startupinfo
                kwargs['creationflags'] = kwargs.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
                return original_popen(*args, **kwargs)
                
            subprocess.Popen = patched_popen
            
            from pyngrok import ngrok, conf
            token = self.ngrok_token_var.get().strip()
            domain = self.ngrok_domain_var.get().strip()
            if token:
                conf.get_default().auth_token = token
            kwargs = {}
            if domain:
                kwargs["domain"] = domain
            url = ngrok.connect(SERVER_PORT, **kwargs).public_url
            self.ngrok_url_var.set(url)
            
            subprocess.Popen = original_popen
        except Exception as e:
            try: subprocess.Popen = original_popen
            except: pass
            self.root.after(1000, lambda: messagebox.showerror("Ngrok 실행 실패", f"Ngrok 중앙 서버를 여는 데 실패했습니다.\n\n{e}\n\n상세 설정에서 Auth Token을 올바르게 입력했는지 확인하세요.", parent=self.root))

    def stop_ngrok(self):
        try:
            from pyngrok import ngrok
            ngrok.kill()
            self.ngrok_url_var.set("")
        except:
            pass

    def toggle_server_mode(self):
        self.save_config()
        if self.is_server_var.get():
            threading.Thread(target=self.start_ngrok_background, daemon=True).start()
        else:
            self.stop_ngrok()

    def reload_config_from_web(self, data):
        """Flask API에서 설정 변경 시 tkinter 변수 업데이트"""
        try:
            self._is_reloading = True
            if 'school_info' in data:
                old_info = getattr(self, 'school_info', {})
                self.school_info = data['school_info']
                # 핵심 정보(학교코드, 학년, 반, API키)가 변경된 경우 시간표 재동기화
                if (old_info.get('school_code') != self.school_info.get('school_code') or
                    old_info.get('grade') != self.school_info.get('grade') or
                    old_info.get('class_nm') != self.school_info.get('class_nm') or
                    old_info.get('api_key') != self.school_info.get('api_key')):
                    
                    self.timetable_cache = {}
                    self.meal_cache = {}
                    if hasattr(self, 'timetable_label') and self.timetable_label.winfo_exists():
                        self.timetable_label.configure(text="시간표 정보를 불러오는 중...")
                    if hasattr(self, 'meal_label') and self.meal_label.winfo_exists():
                        self.meal_label.configure(text="급식 정보를 불러오는 중...")
                    if hasattr(self, 'lbl_school') and self.lbl_school.winfo_exists():
                        school_name = self.school_info.get("name", "학교 미설정")
                        grade = self.school_info.get("grade", "")
                        class_nm = self.school_info.get("class_nm", "")
                        self.lbl_school.configure(text=f"{school_name} {grade}학년 {class_nm}반" if grade else school_name)
                        
                    threading.Thread(target=self.update_timetable_background, daemon=True).start()

            if 'minutes_before' in data:
                self.minutes_var.set(str(data['minutes_before']))
            if 'show_popup_alert' in data:
                self.show_popup_var.set(bool(data['show_popup_alert']))
            if 'autostart' in data:
                self.autostart_var.set(bool(data['autostart']))
            if 'skip_date' in data:
                today = datetime.now().strftime("%Y-%m-%d")
                self.skip_today_var.set(data['skip_date'] == today)
            for day in DAYS:
                if day in data:
                    for class_name, val in data[day].items():
                        if day in self.vars and class_name in self.vars[day]:
                            if isinstance(val, dict):
                                self.vars[day][class_name]["enabled"].set(val.get("enabled", False))
                                self.vars[day][class_name]["action"].set(val.get("action", "시스템 종료"))
            self._is_reloading = False
            self.save_config()
            self.update_status_info()
            self.send_heartbeat_now()
        except Exception as e:
            self._is_reloading = False
            print(f"웹 설정 업데이트 오류: {e}")

    # ── P2P 네트워크 (분산 서버 & 클라이언트) ──────────────────────────
    def flask_server_thread(self):
        try:
            app.run(host='0.0.0.0', port=SERVER_PORT, debug=False, use_reloader=False)
        except Exception as e:
            print(f"Flask 서버 실행 실패: {e}")

    def p2p_listener_thread(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('', BROADCAST_PORT))
        except Exception:
            return
        sock.settimeout(2)
        my_pc_id = socket.gethostname()
        while self.is_running:
            try:
                data, addr = sock.recvfrom(4096)
                try:
                    payload = json.loads(data.decode('utf-8'))
                except Exception:
                    continue
                
                msg_type = payload.get('type')
                if msg_type == 'HEARTBEAT':
                    pc_id = payload.get('pc_id')
                    if pc_id:
                        with data_lock:
                            connected_pcs[pc_id] = {
                                'ip': payload.get('ip', addr[0]),
                                'hostname': payload.get('hostname', pc_id),
                                'user': payload.get('user', ''),
                                'status': payload.get('status', 'online'),
                                'next_event': payload.get('next_event', '-'),
                                'last_seen': datetime.now().strftime('%H:%M:%S'),
                                'last_seen_ts': time.time()
                            }
                elif msg_type == 'COMMAND':
                    target = payload.get('target')
                    action = payload.get('action')
                    message = payload.get('message', '')
                    
                    if target == '__ALL__' or target == my_pc_id:
                        if action == 'shutdown':
                            os.system('shutdown /s /t 0')
                        elif action == 'sleep':
                            os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
                        elif action == 'restart':
                            os.system('shutdown /r /t 0')
                        elif action == 'message' and message:
                            self.root.after(0, lambda m=message: messagebox.showinfo("관리자 메시지", m, parent=self.root))
            except socket.timeout:
                pass
            except Exception:
                time.sleep(1)

    def send_heartbeat_now(self):
        pc_id = socket.gethostname()
        user = os.getlogin()
        ip = get_local_ip()
        next_time, next_action = self.get_next_event()
        next_str = next_time.strftime('%H:%M') if next_time and next_time != "skip" else ("오늘 안 함" if next_time == "skip" else "없음")
        
        payload = json.dumps({
            'type': 'HEARTBEAT',
            'pc_id': pc_id,
            'ip': ip,
            'hostname': pc_id,
            'user': user,
            'status': 'online',
            'next_event': f"{next_str} [{next_action}]" if next_time and next_time != "skip" else next_str
        })
        send_udp_broadcast(payload)

    def p2p_broadcaster_thread(self):
        while self.is_running:
            # 오래된 PC 상태 업데이트 (오프라인 처리)
            now_ts = time.time()
            with data_lock:
                for p_id, info in connected_pcs.items():
                    if now_ts - info.get('last_seen_ts', 0) > OFFLINE_THRESHOLD:
                        info['status'] = 'offline'

            self.send_heartbeat_now()
            time.sleep(2)

    def http_poller_thread(self):
        while self.is_running:
            central_url = self.central_url_var.get().strip()
            if central_url:
                try:
                    if not central_url.startswith("http"): central_url = "http://" + central_url
                    pc_id = socket.gethostname()
                    next_time, next_action = self.get_next_event()
                    next_str = next_time.strftime('%H:%M') if next_time and next_time != "skip" else ("오늘 안 함" if next_time == "skip" else "없음")
                    
                    payload = json.dumps({
                        'pc_id': pc_id,
                        'hostname': pc_id,
                        'user': os.getlogin(),
                        'status': 'online',
                        'next_event': f"{next_str} [{next_action}]" if next_time and next_time != "skip" else next_str
                    }).encode('utf-8')
                    
                    url = f"{central_url.rstrip('/')}/api/heartbeat"
                    req = urllib.request.Request(url, data=payload, method='POST', headers={'Content-Type': 'application/json'})
                    with urllib.request.urlopen(req, timeout=2) as res:
                        resp_data = json.loads(res.read().decode('utf-8'))
                        
                        remote_pcs = resp_data.get("pcs", {})
                        if remote_pcs:
                            now_ts = time.time()
                            with data_lock:
                                for pid, pinfo in remote_pcs.items():
                                    if pid != pc_id:
                                        pinfo['last_seen_ts'] = now_ts
                                        connected_pcs[pid] = pinfo
                                        
                        cmd = resp_data.get("command")
                        if cmd:
                            action = cmd.get("action")
                            message = cmd.get("message", "")
                            if action == 'shutdown': os.system('shutdown /s /t 0')
                            elif action == 'sleep': os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
                            elif action == 'restart': os.system('shutdown /r /t 0')
                            elif action == 'message' and message:
                                self.root.after(0, lambda m=message: messagebox.showinfo("관리자 메시지", m, parent=self.root))
                except Exception:
                    pass
            time.sleep(3)

    def get_timetable_endpoint(self, school_kind):
        if "초등" in school_kind: return "elsTimetable"
        if "중학" in school_kind: return "misTimetable"
        if "고등" in school_kind: return "hisTimetable"
        if "특수" in school_kind: return "spsTimetable"
        return "hisTimetable"

    def fetch_this_week_timetable(self, office_code, school_code, school_kind, grade, class_nm):
        endpoint = self.get_timetable_endpoint(school_kind)
        today = datetime.today()
        monday = today - timedelta(days=today.weekday())
        
        api_key = self.school_info.get("api_key", "").strip()
        cache = {}
        
        if api_key:
            start_date = monday.strftime("%Y%m%d")
            end_date = (monday + timedelta(days=4)).strftime("%Y%m%d")
            url = f"https://open.neis.go.kr/hub/{endpoint}?KEY={api_key}&Type=json&pSize=100&ATPT_OFCDC_SC_CODE={office_code}&SD_SCHUL_CODE={school_code}&GRADE={grade}&CLASS_NM={class_nm}&TI_FROM_YMD={start_date}&TI_TO_YMD={end_date}"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as res:
                    data = json.loads(res.read().decode('utf-8'))
                if endpoint in data:
                    for row in data[endpoint][1]["row"]:
                        ymd = row["ALL_TI_YMD"]
                        perio = row["PERIO"]
                        subj = row["ITRT_CNTNT"]
                        if ymd not in cache: cache[ymd] = {}
                        cache[ymd][perio] = subj
                elif "RESULT" in data and "CODE" in data["RESULT"]:
                    code = data["RESULT"]["CODE"]
                    msg = data["RESULT"]["MESSAGE"]
                    if code == "ERROR-290":
                        if getattr(self, 'api_key_error_shown', False) is False:
                            self.root.after(0, lambda: messagebox.showwarning("API 키 오류", f"나이스 API 키에 문제가 있습니다.\n(오류코드: {code})\n\n{msg}\n\n※ 인증키를 방금 발급받았다면 1~2시간 뒤에 활성화될 수 있습니다.\n임시로 5교시까지만 불러옵니다.", parent=self.root))
                            self.api_key_error_shown = True
                    api_key = "" # Fallback to no-key logic
            except Exception as e:
                print("시간표(KEY) 불러오기 실패:", e)
                api_key = "" # Fallback
                
        if not api_key:
            for i in range(5):
                date_str = (monday + timedelta(days=i)).strftime("%Y%m%d")
                url = f"https://open.neis.go.kr/hub/{endpoint}?Type=json&pSize=5&ATPT_OFCDC_SC_CODE={office_code}&SD_SCHUL_CODE={school_code}&GRADE={grade}&CLASS_NM={class_nm}&TI_FROM_YMD={date_str}&TI_TO_YMD={date_str}"
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=3) as res:
                        data = json.loads(res.read().decode('utf-8'))
                    if endpoint in data:
                        for row in data[endpoint][1]["row"]:
                            ymd = row["ALL_TI_YMD"]
                            perio = row["PERIO"]
                            subj = row["ITRT_CNTNT"]
                            if ymd not in cache: cache[ymd] = {}
                            cache[ymd][perio] = subj
                except Exception as e:
                    print(f"시간표({date_str}) 불러오기 실패:", e)

        return cache if cache else None

    def clean_meal_text(self, text):
        text = text.replace("<br/>", ", ").replace("<br>", ", ")
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r',\s*,', ',', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text.strip(", ")

    def fetch_this_week_meals(self, office_code, school_code):
        today = datetime.today()
        monday = today - timedelta(days=today.weekday())
        api_key = self.school_info.get("api_key", "").strip()
        cache = {}
        
        if api_key:
            start_date = monday.strftime("%Y%m%d")
            end_date = (monday + timedelta(days=4)).strftime("%Y%m%d")
            url = f"https://open.neis.go.kr/hub/mealServiceDietInfo?KEY={api_key}&Type=json&pSize=100&ATPT_OFCDC_SC_CODE={office_code}&SD_SCHUL_CODE={school_code}&MLSV_FROM_YMD={start_date}&MLSV_TO_YMD={end_date}"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as res:
                    data = json.loads(res.read().decode('utf-8'))
                if "mealServiceDietInfo" in data:
                    for row in data["mealServiceDietInfo"][1]["row"]:
                        ymd = row["MLSV_YMD"]
                        mmeal_nm = row["MMEAL_SC_NM"]
                        dish = self.clean_meal_text(row["DDISH_NM"])
                        if ymd not in cache: cache[ymd] = {}
                        cache[ymd][mmeal_nm] = dish
                elif "RESULT" in data and "CODE" in data["RESULT"]:
                    api_key = "" # Fallback
            except Exception as e:
                print("급식(KEY) 불러오기 실패:", e)
                api_key = "" # Fallback
                
        if not api_key:
            for i in range(5):
                date_str = (monday + timedelta(days=i)).strftime("%Y%m%d")
                url = f"https://open.neis.go.kr/hub/mealServiceDietInfo?Type=json&pSize=5&ATPT_OFCDC_SC_CODE={office_code}&SD_SCHUL_CODE={school_code}&MLSV_FROM_YMD={date_str}&MLSV_TO_YMD={date_str}"
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=3) as res:
                        data = json.loads(res.read().decode('utf-8'))
                    if "mealServiceDietInfo" in data:
                        for row in data["mealServiceDietInfo"][1]["row"]:
                            ymd = row["MLSV_YMD"]
                            mmeal_nm = row["MMEAL_SC_NM"]
                            dish = self.clean_meal_text(row["DDISH_NM"])
                            if ymd not in cache: cache[ymd] = {}
                            cache[ymd][mmeal_nm] = dish
                except Exception as e:
                    print(f"급식({date_str}) 불러오기 실패:", e)
        return cache if cache else None

    def update_timetable_background(self):
        office_code = self.school_info.get("office_code")
        school_code = self.school_info.get("school_code")
        grade = self.school_info.get("grade")
        class_nm = self.school_info.get("class_nm")
        
        if not office_code or not school_code or not grade or not class_nm:
            self.root.after(0, self.update_timetable_ui)
            return

        cache = self.fetch_this_week_timetable(
            office_code,
            school_code,
            self.school_info.get("school_kind"),
            grade,
            class_nm
        )
        meal_cache = self.fetch_this_week_meals(
            self.school_info.get("office_code"),
            self.school_info.get("school_code")
        )
        if cache:
            self.timetable_cache = cache
        if meal_cache:
            self.meal_cache = meal_cache
            
        if cache or meal_cache:
            self.save_config()
            self.root.after(0, self.update_timetable_ui)

    def update_timetable_ui(self):
        today_str = datetime.today().strftime("%Y%m%d")
        if today_str in self.timetable_cache:
            subjects = []
            for p in sorted(self.timetable_cache[today_str].keys(), key=int):
                subjects.append(f"{p}교시:{self.timetable_cache[today_str][p]}")
            text = "오늘 시간표: " + ", ".join(subjects)
            if hasattr(self, 'timetable_label'):
                self.timetable_label.configure(text=text)
        else:
            if hasattr(self, 'timetable_label'):
                self.timetable_label.configure(text="오늘의 시간표 정보가 없습니다.")
                
        if today_str in getattr(self, 'meal_cache', {}):
            meals = self.meal_cache[today_str]
            meal_texts = []
            if "조식" in meals: meal_texts.append(f"[조식] {meals['조식']}")
            if "중식" in meals: meal_texts.append(f"[중식] {meals['중식']}")
            if "석식" in meals: meal_texts.append(f"[석식] {meals['석식']}")
            
            if meal_texts:
                text = "\n".join(meal_texts)
            else:
                text = "오늘의 급식 정보가 없습니다."
                
            if hasattr(self, 'meal_label'):
                self.meal_label.configure(text=text)
        else:
            if hasattr(self, 'meal_label'):
                self.meal_label.configure(text="오늘의 급식 정보가 없습니다.")
                
        if hasattr(self, 'subject_labels'):
            today = datetime.today()
            monday = today - timedelta(days=today.weekday())
            for i, day in enumerate(DAYS[:5]):
                ymd = (monday + timedelta(days=i)).strftime("%Y%m%d")
                for class_name, _ in TIMETABLE.items():
                    subj = ""
                    if ymd in self.timetable_cache:
                        if "1교시" in class_name: subj = self.timetable_cache[ymd].get("1", "")
                        elif "2교시" in class_name: subj = self.timetable_cache[ymd].get("2", "")
                        elif "3교시" in class_name: subj = self.timetable_cache[ymd].get("3", "")
                        elif "4교시" in class_name: subj = self.timetable_cache[ymd].get("4", "")
                        elif "5교시" in class_name: subj = self.timetable_cache[ymd].get("5", "")
                        elif "6교시" in class_name: subj = self.timetable_cache[ymd].get("6", "")
                        elif "7교시" in class_name: subj = self.timetable_cache[ymd].get("7", "")
                        elif "8교시" in class_name: subj = self.timetable_cache[ymd].get("8", "")
                    
                    if day in self.subject_labels and class_name in self.subject_labels[day]:
                        lbl = self.subject_labels[day][class_name]
                        if lbl.winfo_exists():
                            lbl.configure(text=f"({subj})" if subj else "")

    def check_for_updates(self):
        try:
            # 캐시 방지를 위해 타임스탬프 추가
            url = f"https://raw.githubusercontent.com/JunHyuk1203/autoshutdown/main/version.json?t={int(time.time())}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                remote_version = data.get("version", CURRENT_VERSION)
                download_url = data.get("download_url")
                
            if self._is_newer_version(remote_version, CURRENT_VERSION) and download_url:
                self.perform_auto_update(download_url)
        except Exception as e:
            print("업데이트 확인 실패:", e)

    def _is_newer_version(self, remote, current):
        r_parts = [int(x) for x in remote.split('.')]
        c_parts = [int(x) for x in current.split('.')]
        return r_parts > c_parts

    def _show_update_error(self, msg):
        """업데이트 실패 알림 (메인 스레드에서 실행)"""
        try:
            self.root.after(0, lambda: messagebox.showerror("업데이트 실패", msg, parent=self.root))
        except: pass

    def perform_auto_update(self, download_url, is_manual=False):
        update_exe_path = os.path.join(application_path, "update_temp.exe")
        try:
            # 1. 새 버전 다운로드
            # 캐시 방지를 위해 다운로드 URL에도 타임스탬프 추가
            if "?" in download_url:
                no_cache_url = f"{download_url}&t={int(time.time())}"
            else:
                no_cache_url = f"{download_url}?t={int(time.time())}"
                
            req = urllib.request.Request(no_cache_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=120) as response:
                data = response.read()
            
            # 2. 다운로드 무결성 검증 (최소 크기 체크 — 정상 exe는 수 MB 이상)
            if len(data) < 1_000_000:
                self._show_update_error(f"다운로드된 파일이 너무 작습니다 ({len(data)} bytes).\n네트워크 오류일 수 있습니다. 다시 시도해주세요.")
                return
            
            with open(update_exe_path, 'wb') as out_file:
                out_file.write(data)
            
            # 디스크에 기록된 파일 크기 재확인
            if os.path.getsize(update_exe_path) != len(data):
                self._show_update_error("다운로드 파일 저장 중 오류가 발생했습니다.\n디스크 공간을 확인해주세요.")
                os.remove(update_exe_path)
                return
                
            current_exe = sys.executable if getattr(sys, 'frozen', False) else None
            
            if current_exe and current_exe.endswith('.exe'):
                old_exe_path = current_exe + ".old"
                
                # 3. 이전 .old 파일 정리
                if os.path.exists(old_exe_path):
                    try: os.remove(old_exe_path)
                    except: pass
                
                # 4. 원자적 파일 교체 (실패 시 롤백)
                renamed_current = False
                try:
                    os.rename(current_exe, old_exe_path)
                    renamed_current = True
                    os.rename(update_exe_path, current_exe)
                except Exception as e:
                    # 롤백: 현재 exe가 이미 .old로 옮겨졌으면 원래대로 복구
                    if renamed_current and not os.path.exists(current_exe):
                        try:
                            os.rename(old_exe_path, current_exe)
                        except: pass
                    if os.path.exists(update_exe_path):
                        try: os.remove(update_exe_path)
                        except: pass
                    self._show_update_error(f"실행 파일 교체에 실패했습니다.\n프로그램이 다른 곳에서 사용 중일 수 있습니다.\n\n오류: {e}")
                    return  # 교체 실패 시 여기서 중단 (프로그램 종료하지 않음)
                
                # 5. 파일 교체 성공 → 새 프로세스 실행
                # 매우 중요: PyInstaller 6+ 에서는 _PYI_APPLICATION_HOME_DIR 등 여러 환경변수를 사용합니다.
                # 이 변수들이 새 프로세스로 넘어가면, 새 프로세스는 압축 풀기를 생략하고 
                # 이전 프로세스(곧 종료되어 삭제될)의 _MEI 폴더를 참조하다가 DLL 로드 에러가 발생합니다.
                # 따라서 현재 환경변수에서 PyInstaller 관련 변수를 모두 제거한 후 실행해야 합니다.
                clean_env = os.environ.copy()
                keys_to_remove = [k for k in clean_env if 'MEI' in k or 'PYI' in k or 'TCL' in k or 'TK' in k]
                for k in keys_to_remove:
                    clean_env.pop(k, None)
                
                # 완전히 독립된 새 프로세스로 실행 (창 없이, 새 그룹)
                args = [current_exe]
                if is_manual:
                    args.append("--just-updated")
                
                subprocess.Popen(
                    args,
                    env=clean_env,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                )
                
                self.quit_app()
        except Exception as e:
            # 실패 시 임시 파일 정리
            if os.path.exists(update_exe_path):
                try: os.remove(update_exe_path)
                except: pass
            self._show_update_error(f"업데이트 중 오류가 발생했습니다.\n인터넷 연결을 확인해주세요.\n\n오류: {e}")

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    # 마이그레이션: 이전 버전의 "1교시" 키를 "1교시 (08:40)" 등으로 변환
                    for day in DAYS:
                        if day in config and isinstance(config[day], dict):
                            new_day_config = {}
                            for old_key, val in config[day].items():
                                matched = False
                                for new_key in TIMETABLE.keys():
                                    if old_key.split(' ')[0] == new_key.split(' ')[0]:
                                        new_day_config[new_key] = val
                                        matched = True
                                        break
                                if not matched:
                                    new_day_config[old_key] = val
                            config[day] = new_day_config
                    
                    return config
        except Exception: pass
        return {}

    def save_config_callback(self, *args):
        if getattr(self, '_is_reloading', False): return
        self.save_config()

    def save_config(self):
        try:
            try: mins = int(self.minutes_var.get())
            except: mins = 2
                
            new_config = {
                "minutes_before": mins,
                "autostart": self.autostart_var.get(),
                "show_popup_alert": self.show_popup_var.get(),
                "skip_date": datetime.now().strftime("%Y-%m-%d") if self.skip_today_var.get() else "",
                "central_server_url": self.central_url_var.get().strip(),
                "ngrok_token": self.ngrok_token_var.get().strip(),
                "ngrok_domain": self.ngrok_domain_var.get().strip(),
                "is_server": self.is_server_var.get(),
                "school_info": getattr(self, 'school_info', {}),
                "timetable_cache": getattr(self, 'timetable_cache', {}),
                "meal_cache": getattr(self, 'meal_cache', {})
            }
                
            for day in DAYS:
                new_config[day] = {}
                for class_name in TIMETABLE.keys():
                    new_config[day][class_name] = {
                        "enabled": self.vars[day][class_name]["enabled"].get(),
                        "action": self.vars[day][class_name]["action"].get()
                    }
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, ensure_ascii=False, indent=4)
                
            self.update_autostart_shortcut(new_config["autostart"])
            self.update_status_info()
        except Exception: pass

    def update_autostart_shortcut(self, enable):
        startup_dir = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        vbs_path = os.path.join(startup_dir, "AutoShutdownBG.vbs")
        if enable:
            if getattr(sys, 'frozen', False):
                exe_path = os.path.join(application_path, "auto_shutdown.exe")
                # 부팅 시 Explorer 쉘이 준비될 시간을 주기 위해 5초 대기 후 실행
                script = f'WScript.Sleep 5000\nSet WshShell = CreateObject("WScript.Shell")\nWshShell.Run chr(34) & "{exe_path}" & Chr(34), 0\nSet WshShell = Nothing'
            else:
                bg_script = os.path.join(application_path, "auto_shutdown.py")
                pythonw = sys.executable.replace("python.exe", "pythonw.exe")
                script = f'WScript.Sleep 5000\nSet WshShell = CreateObject("WScript.Shell")\nWshShell.Run chr(34) & "{pythonw}" & Chr(34) & " " & chr(34) & "{bg_script}" & chr(34), 0\nSet WshShell = Nothing'
            with open(vbs_path, 'w', encoding='utf-8') as f:
                f.write(script)
        else:
            if os.path.exists(vbs_path): os.remove(vbs_path)

    def toggle_skip_today_dashboard(self):
        self.save_config()
        self.update_status_info()

    def get_skip_state(self, item): return self.skip_today_var.get()
    def toggle_skip_state(self, icon, item):
        self.skip_today_var.set(not self.skip_today_var.get())
        self.save_config()
        self.update_status_info()

    def skip_next_schedule(self):
        next_time, next_action = self.get_next_event()
        if next_time and next_time != "skip":
            self.skipped_events.add(next_time.strftime("%Y-%m-%d %H:%M"))
            msg = f"예정된 {next_time.strftime('%H:%M')} 일정을"
                
            self.update_status_info()
            if self.icon: self.icon.notify(f"{msg} 건너뛰었습니다.", "알림")
            else: messagebox.showinfo("안내", f"{msg} 1회 건너뜁니다.", parent=self.root)

    def open_settings_window(self):
        if getattr(self, 'settings_win', None) and self.settings_win.winfo_exists():
            self.settings_win.focus()
            return
            
        self.settings_win = ctk.CTkToplevel(self.root)
        self.settings_win.title("상세 설정")
        self.settings_win.geometry("380x550")
        self.settings_win.resizable(False, False)
        self.settings_win.attributes('-topmost', True)
        self.settings_win.after(100, lambda: self.settings_win.attributes('-topmost', False))
        
        scroll = ctk.CTkScrollableFrame(self.settings_win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        popup_card = ctk.CTkFrame(scroll, fg_color=("gray95", "gray15"), corner_radius=15)
        popup_card.pack(fill="x", pady=5, ipady=5)
        ctk.CTkLabel(popup_card, text="🔔 알림 설정", font=ctk.CTkFont(family=self.font_family, size=13, weight="bold")).pack(pady=(10, 5))
        
        popup_chk = ctk.CTkSwitch(popup_card, text="화면 중앙 팝업 알림 표시", variable=self.show_popup_var, font=ctk.CTkFont(family=self.font_family, size=11), switch_width=32, switch_height=16)
        popup_chk.pack(pady=5)
        ctk.CTkLabel(popup_card, text="※ 끄더라도 스케줄은 1분의 유예시간이\n백그라운드에서 동일하게 작동합니다.", font=ctk.CTkFont(family=self.font_family, size=10), text_color="gray").pack(pady=(0, 5))
        
        neis_card = ctk.CTkFrame(scroll, fg_color=("#E8F5E9", "#1E3A2F"), corner_radius=15, border_width=1, border_color="#2ECC71")
        neis_card.pack(fill="x", pady=5, ipady=5)
        ctk.CTkLabel(neis_card, text="🏫 나이스(NEIS) 학교 및 시간표 연동", font=ctk.CTkFont(family=self.font_family, size=12, weight="bold")).pack(pady=(8, 2))
        
        neis_info_frame = ctk.CTkFrame(neis_card, fg_color="transparent")
        neis_info_frame.pack(fill="x", padx=10, pady=5)
        
        school_name = self.school_info.get("name", "학교 미설정")
        grade = self.school_info.get("grade", "")
        class_nm = self.school_info.get("class_nm", "")
        
        self.lbl_school = ctk.CTkLabel(neis_info_frame, text=f"{school_name} {grade}학년 {class_nm}반" if grade else school_name, font=ctk.CTkFont(family=self.font_family, size=11))
        self.lbl_school.pack(side="left", padx=5)
        
        btn_search_school = ctk.CTkButton(neis_info_frame, text="학교 검색", command=self.open_school_search, width=70, height=24, font=ctk.CTkFont(family=self.font_family, size=11))
        btn_search_school.pack(side="right", padx=5)
        
        api_key_frame = ctk.CTkFrame(neis_card, fg_color="transparent")
        api_key_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(api_key_frame, text="API KEY:", font=ctk.CTkFont(family=self.font_family, size=11)).pack(side="left", padx=5)
        self.api_key_entry = ctk.CTkEntry(api_key_frame, placeholder_text="선택사항 (6~7교시 조회용)", font=ctk.CTkFont(family=self.font_family, size=10), height=24)
        self.api_key_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.api_key_entry.insert(0, self.school_info.get("api_key", ""))
        
        def save_api_key():
            self.school_info["api_key"] = self.api_key_entry.get().strip()
            self.api_key_error_shown = False
            self.save_config()
            self.timetable_cache = {}
            if hasattr(self, 'timetable_label'):
                self.timetable_label.configure(text="시간표 다시 불러오는 중...")
            threading.Thread(target=self.update_timetable_background, daemon=True).start()
            messagebox.showinfo("저장", "API 키가 저장되고 데이터를 다시 불러옵니다.\n※ 인증키를 방금 발급받았다면 1~2시간 뒤에 활성화될 수 있습니다.", parent=self.settings_win)
            
        ctk.CTkButton(api_key_frame, text="키 적용", command=save_api_key, width=50, height=24, font=ctk.CTkFont(family=self.font_family, size=11)).pack(side="right", padx=5)
        
        # 방화벽 설정 카드
        firewall_card = ctk.CTkFrame(scroll, fg_color=("gray95", "gray15"), corner_radius=15)
        firewall_card.pack(fill="x", pady=5, ipady=5)
        ctk.CTkLabel(firewall_card, text="🛡️ 원격 제어 방화벽 설정", font=ctk.CTkFont(family=self.font_family, size=12, weight="bold")).pack(pady=(8, 2))
        
        status_lbl = ctk.CTkLabel(firewall_card, text="상태 확인 중...", font=ctk.CTkFont(family=self.font_family, size=11))
        status_lbl.pack(pady=2)

        def check_firewall_status():
            try:
                result = subprocess.run(
                    ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=SmartPowerControl_TCP'],
                    capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
                # returncode 0 = 규칙 존재(허용), 1 = 규칙 없음(차단)
                if result.returncode == 0:
                    status_lbl.configure(text="현재 상태: ✅ 허용됨 (스마트폰 등 접속 가능)", text_color="#2ECC71")
                else:
                    status_lbl.configure(text="현재 상태: ❌ 차단됨 (접속 불가 - 허용 필요)", text_color="#E74C3C")
            except Exception as e:
                status_lbl.configure(text=f"상태 확인 실패: {e}", text_color="gray")

        def check_loop(count=0):
            check_firewall_status()
            if count < 5:
                # 1초마다 다시 확인 (관리자 권한 승인하는 시간 고려)
                if getattr(self, 'settings_win', None) and self.settings_win.winfo_exists():
                    self.settings_win.after(1000, lambda: check_loop(count + 1))

        def setup_firewall_and_test():
            try:
                commands = (
                    "netsh advfirewall firewall add rule name=\"SmartPowerControl_TCP\" dir=in action=allow protocol=TCP localport=5000 & "
                    "netsh advfirewall firewall add rule name=\"SmartPowerControl_UDP\" dir=in action=allow protocol=UDP localport=5555"
                )
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f"/c {commands}", None, 0)
                # 실행 후 상태 확인 루프 시작
                if getattr(self, 'settings_win', None) and self.settings_win.winfo_exists():
                    self.settings_win.after(1000, lambda: check_loop(0))
            except Exception:
                pass

        btn_frame = ctk.CTkFrame(firewall_card, fg_color="transparent")
        btn_frame.pack(pady=5)
        
        ctk.CTkButton(btn_frame, text="방화벽 허용 (관리자 권한)", command=setup_firewall_and_test, font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"), fg_color="#34495E", hover_color="#2C3E50", height=28).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="상태 새로고침", command=check_firewall_status, font=ctk.CTkFont(family=self.font_family, size=11), fg_color="gray", hover_color="#555", height=28).pack(side="left", padx=5)

        # UI 렌더링 후 초기 상태 확인
        self.settings_win.after(100, check_firewall_status)
        
        # Ngrok 및 HTTP 서버 카드
        ngrok_card = ctk.CTkFrame(scroll, fg_color=("gray95", "gray15"), corner_radius=15)
        ngrok_card.pack(fill="x", pady=5, ipady=5)
        ctk.CTkLabel(ngrok_card, text="🌐 원격 중앙 제어 (방화벽 무시)", font=ctk.CTkFont(family=self.font_family, size=12, weight="bold")).pack(pady=(8, 2))
        
        mode_frame = ctk.CTkFrame(ngrok_card, fg_color="transparent")
        mode_frame.pack(fill="x", padx=10, pady=(5,0))
        ctk.CTkSwitch(mode_frame, text="이 PC를 메인 서버로 사용 (Ngrok 실행)", variable=self.is_server_var, font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"), command=self.toggle_server_mode).pack(side="left", padx=5)
        
        ngrok_desc = "메인 서버로 설정된 PC 1대에서만 Ngrok을 실행해야 충돌이 발생하지 않습니다.\n나머지 PC는 하단에 중앙 서버 주소만 입력하세요."
        ctk.CTkLabel(ngrok_card, text=ngrok_desc, font=ctk.CTkFont(family=self.font_family, size=10), text_color="gray").pack(pady=2)

        ngrok_btn_frame = ctk.CTkFrame(ngrok_card, fg_color="transparent")
        ngrok_btn_frame.pack(pady=5)
        
        ctk.CTkLabel(ngrok_btn_frame, text="현재 Ngrok 주소:", font=ctk.CTkFont(family=self.font_family, size=11, weight="bold")).pack(side="left", padx=5)
        
        url_lbl = ctk.CTkEntry(ngrok_btn_frame, textvariable=self.ngrok_url_var, state="readonly", width=180, font=ctk.CTkFont(family=self.font_family, size=11))
        url_lbl.pack(side="left", padx=5)
        
        token_frame = ctk.CTkFrame(ngrok_card, fg_color="transparent")
        token_frame.pack(fill="x", padx=10, pady=(5, 0))
        ctk.CTkLabel(token_frame, text="Auth Token:", font=ctk.CTkFont(family=self.font_family, size=11)).pack(side="left", padx=5)
        ctk.CTkEntry(token_frame, textvariable=self.ngrok_token_var, placeholder_text="(선택) Ngrok 홈페이지 발급 토큰", font=ctk.CTkFont(family=self.font_family, size=11)).pack(side="left", fill="x", expand=True, padx=5)
        
        domain_frame = ctk.CTkFrame(ngrok_card, fg_color="transparent")
        domain_frame.pack(fill="x", padx=10, pady=(5, 5))
        ctk.CTkLabel(domain_frame, text="고정 도메인:", font=ctk.CTkFont(family=self.font_family, size=11)).pack(side="left", padx=5)
        ctk.CTkEntry(domain_frame, textvariable=self.ngrok_domain_var, placeholder_text="(선택) 예: lobster.ngrok-free.app", font=ctk.CTkFont(family=self.font_family, size=11)).pack(side="left", fill="x", expand=True, padx=5)
        
        self.ngrok_token_var.trace_add('write', self.save_config_callback)
        self.ngrok_domain_var.trace_add('write', self.save_config_callback)

        client_frame = ctk.CTkFrame(ngrok_card, fg_color="transparent")
        client_frame.pack(fill="x", padx=10, pady=(5, 5))
        ctk.CTkLabel(client_frame, text="중앙 서버 주소:", font=ctk.CTkFont(family=self.font_family, size=11)).pack(side="left", padx=5)
        central_url_entry = ctk.CTkEntry(client_frame, textvariable=self.central_url_var, placeholder_text="예: https://xxx.ngrok.app", font=ctk.CTkFont(family=self.font_family, size=11))
        central_url_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.central_url_var.trace_add('write', self.save_config_callback)
        
        schedule_card = ctk.CTkFrame(scroll, fg_color=("gray95", "gray15"), corner_radius=15)
        schedule_card.pack(fill="x", pady=5, ipady=5)
        ctk.CTkLabel(schedule_card, text="📅 주간 스케줄 예약", font=ctk.CTkFont(family=self.font_family, size=12, weight="bold")).pack(pady=(8, 2))
        
        min_frame = ctk.CTkFrame(schedule_card, fg_color="transparent")
        min_frame.pack(pady=2)
        ctk.CTkLabel(min_frame, text="체크한 시간의", font=ctk.CTkFont(family=self.font_family, size=11)).pack(side="left", padx=5)
        
        minutes_options = [str(i) for i in range(11)] + ["15", "20", "30", "45", "60", "90", "120"]
        if self.minutes_var.get() not in minutes_options:
            minutes_options.append(self.minutes_var.get())
            minutes_options.sort(key=int)
            
        min_opt = ctk.CTkOptionMenu(min_frame, variable=self.minutes_var, values=minutes_options, width=60, height=24, font=ctk.CTkFont(family=self.font_family, size=11))
        min_opt.pack(side="left", padx=5)
        ctk.CTkLabel(min_frame, text="분 전에 제어 실행", font=ctk.CTkFont(family=self.font_family, size=11)).pack(side="left", padx=5)
        
        self.tabview = ctk.CTkTabview(schedule_card, width=300, height=180)
        self.tabview.pack(pady=2, padx=10, fill="both", expand=True)
        
        for day in DAYS:
            self.tabview.add(day)
            tab_frame = self.tabview.tab(day)
            for class_name, _ in TIMETABLE.items():
                row_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
                row_frame.pack(anchor="w", fill="x", pady=4, padx=5)
                var_en = self.vars[day][class_name]["enabled"]
                var_act = self.vars[day][class_name]["action"]
                chk = ctk.CTkSwitch(row_frame, text=class_name, variable=var_en, font=ctk.CTkFont(family=self.font_family, size=11), switch_width=32, switch_height=16)
                chk.pack(side="left")
                
                subj_lbl = ctk.CTkLabel(row_frame, text="", font=ctk.CTkFont(family=self.font_family, size=10), text_color="#3498DB")
                subj_lbl.pack(side="left", padx=5)
                self.subject_labels[day][class_name] = subj_lbl
                
                cb = ctk.CTkOptionMenu(row_frame, variable=var_act, values=["시스템 종료", "절전 모드"], width=70, height=24, font=ctk.CTkFont(family=self.font_family, size=11))
                cb.pack(side="right")
                
        self.update_timetable_ui()
        
        auto_chk = ctk.CTkSwitch(scroll, text="윈도우 시작 시 백그라운드로 자동 실행", variable=self.autostart_var, font=ctk.CTkFont(family=self.font_family, size=11), switch_width=32, switch_height=16)
        auto_chk.pack(pady=(10, 5))

        update_card = ctk.CTkFrame(scroll, fg_color=("gray95", "gray15"), corner_radius=15)
        update_card.pack(fill="x", pady=5, ipady=5)
        ctk.CTkLabel(update_card, text=f"ℹ️ 현재 버전: v{CURRENT_VERSION}", font=ctk.CTkFont(family=self.font_family, size=12, weight="bold")).pack(pady=(8, 2))
        update_btn = ctk.CTkButton(update_card, text="🔄 수동 업데이트 확인", command=self.manual_update_check, width=150, height=28, font=ctk.CTkFont(family=self.font_family, size=11))
        update_btn.pack(pady=(5, 8))

    def open_school_search(self):
        search_win = ctk.CTkToplevel(self.settings_win)
        search_win.title("학교 검색")
        search_win.geometry("300x350")
        search_win.attributes('-topmost', True)
        search_win.grab_set()
        
        entry = ctk.CTkEntry(search_win, placeholder_text="학교명 입력 (예: 서울과학고)")
        entry.pack(pady=10, padx=10, fill="x")
        
        result_frame = ctk.CTkScrollableFrame(search_win)
        result_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        def select_school(row):
            search_win.destroy()
            self.ask_grade_class(row)
            
        def do_search():
            q = entry.get().strip()
            if not q: return
            url = f"https://open.neis.go.kr/hub/schoolInfo?Type=json&pIndex=1&pSize=20&SCHUL_NM={urllib.parse.quote(q)}"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as res:
                    data = json.loads(res.read().decode('utf-8'))
                
                for widget in result_frame.winfo_children():
                    widget.destroy()
                    
                if "schoolInfo" in data:
                    rows = data["schoolInfo"][1]["row"]
                    for r in rows:
                        name = r["SCHUL_NM"]
                        addr = r["ORG_RDNMA"]
                        btn = ctk.CTkButton(result_frame, text=f"{name}\n({addr})", anchor="w", command=lambda row=r: select_school(row))
                        btn.pack(fill="x", pady=2)
                else:
                    ctk.CTkLabel(result_frame, text="검색 결과가 없습니다.").pack()
            except Exception as e:
                print(e)
                
        btn_search = ctk.CTkButton(search_win, text="검색", command=do_search)
        btn_search.pack(pady=5)

    def ask_grade_class(self, row):
        gc_win = ctk.CTkToplevel(self.settings_win)
        gc_win.title("학년/반 입력")
        gc_win.geometry("250x200")
        gc_win.attributes('-topmost', True)
        gc_win.grab_set()
        
        ctk.CTkLabel(gc_win, text=row["SCHUL_NM"], font=ctk.CTkFont(family=self.font_family, weight="bold")).pack(pady=10)
        
        frame = ctk.CTkFrame(gc_win, fg_color="transparent")
        frame.pack(pady=10)
        
        ctk.CTkLabel(frame, text="학년:").grid(row=0, column=0, padx=5, pady=5)
        grade_entry = ctk.CTkEntry(frame, width=50)
        grade_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(frame, text="반:").grid(row=1, column=0, padx=5, pady=5)
        class_entry = ctk.CTkEntry(frame, width=50)
        class_entry.grid(row=1, column=1, padx=5, pady=5)
        
        def save_and_fetch():
            g = grade_entry.get().strip()
            c = class_entry.get().strip()
            if not g or not c:
                messagebox.showerror("오류", "학년과 반을 모두 입력해주세요.", parent=gc_win)
                return
            
            self.school_info = {
                "name": row["SCHUL_NM"],
                "office_code": row["ATPT_OFCDC_SC_CODE"],
                "school_code": row["SD_SCHUL_CODE"],
                "school_kind": row["SCHUL_KND_SC_NM"],
                "grade": g,
                "class_nm": c
            }
            self.save_config()
            if hasattr(self, 'lbl_school'):
                self.lbl_school.configure(text=f"{row['SCHUL_NM']} {g}학년 {c}반")
            gc_win.destroy()
            
            self.timetable_cache = {}
            if hasattr(self, 'timetable_label'):
                self.timetable_label.configure(text="시간표 정보를 불러오는 중...")
            threading.Thread(target=self.update_timetable_background, daemon=True).start()
            
        btn = ctk.CTkButton(gc_win, text="저장 및 연동", command=save_and_fetch)
        btn.pack(pady=10)

    def manual_update_check(self):
        try:
            # 캐시 방지를 위해 타임스탬프 추가
            url = f"https://raw.githubusercontent.com/JunHyuk1203/autoshutdown/main/version.json?t={int(time.time())}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                remote_version = data.get("version", CURRENT_VERSION)
                download_url = data.get("download_url")
                
            if self._is_newer_version(remote_version, CURRENT_VERSION) and download_url:
                if messagebox.askyesno("업데이트 알림", f"새로운 버전(v{remote_version})이 발견되었습니다!\n지금 바로 업데이트하시겠습니까?", parent=getattr(self, 'settings_win', self.root)):
                    self.perform_auto_update(download_url, is_manual=True)
            elif download_url:
                if messagebox.askyesno("업데이트 확인", f"현재 최신 버전(v{CURRENT_VERSION})을 사용 중입니다.\n강제로 최신 버전을 다시 다운로드하여 재설치하시겠습니까?", parent=getattr(self, 'settings_win', self.root)):
                    self.perform_auto_update(download_url, is_manual=True)
            else:
                messagebox.showinfo("업데이트 오류", "다운로드 링크를 찾을 수 없습니다.", parent=getattr(self, 'settings_win', self.root))
        except Exception as e:
            messagebox.showerror("업데이트 오류", f"서버와 통신 중 오류가 발생했습니다.\n인터넷 연결 상태를 확인해 주세요.\n{e}", parent=getattr(self, 'settings_win', self.root))

    def cancel_shutdown(self, icon=None, item=None):
        self.pending_shutdown = False
        if self.icon: self.icon.notify("예약된 시스템 종료/절전이 취소되었습니다.", "종료 취소")

    def get_menu(self):
        local_ip = get_local_ip()
        remote_url = f"http://{local_ip}:{SERVER_PORT}"
        
        def open_remote():
            import webbrowser
            webbrowser.open(remote_url)
            
        menu_items = [
            pystray.MenuItem(f'🌐 원격 제어: {remote_url}', open_remote),
            pystray.MenuItem('오늘 하루 끄지 않기', self.toggle_skip_state, checked=self.get_skip_state),
            pystray.MenuItem('열기 (대시보드)', self.show_window)
        ]
        menu_items.append(pystray.MenuItem('❌ 대기열에 있는 제어 강제 취소', self.cancel_shutdown, visible=lambda item: getattr(self, 'pending_shutdown', False)))
        menu_items.append(pystray.MenuItem('종료', self.quit_app))
        return tuple(menu_items)

    def _show_update_success_popup(self):
        popup = ctk.CTkToplevel(self.root)
        popup.title("업데이트 성공")
        popup.geometry("300x150")
        popup.attributes('-topmost', True)
        popup.resizable(False, False)
        
        # 화면 중앙에 배치
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 300) // 2
        y = (screen_height - 150) // 2
        popup.geometry(f"+{x}+{y}")
        
        lbl = ctk.CTkLabel(popup, text="🎉 업데이트 완료!", font=ctk.CTkFont(family=self.font_family, size=16, weight="bold"), text_color="#2ECC71")
        lbl.pack(pady=(20, 10))
        
        lbl2 = ctk.CTkLabel(popup, text=f"v{CURRENT_VERSION}으로 성공적으로 업데이트되었습니다.", font=ctk.CTkFont(family=self.font_family, size=12))
        lbl2.pack(pady=(0, 20))
        
        btn = ctk.CTkButton(popup, text="확인", command=popup.destroy, width=100)
        btn.pack()

    def _is_shell_ready(self):
        """Explorer 쉘(시스템 트레이)이 준비되었는지 확인"""
        hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        return hwnd != 0

    def _create_tray_icon_with_retry(self, attempt=0):
        """트레이 아이콘 생성 — 쉘 미준비 시 재시도 (부팅 직후 대비)"""
        MAX_RETRIES = 30  # 최대 30회, 약 60초

        if not self._is_shell_ready():
            if attempt < MAX_RETRIES:
                self.root.after(2000, lambda: self._create_tray_icon_with_retry(attempt + 1))
                return
            # 최대 재시도 초과 — 그래도 한 번 시도

        try:
            image = self.create_image(64, 64)
            menu = pystray.Menu(self.get_menu)
            self.icon = pystray.Icon("autoshutdown_v2", image, "스마트 전원 관리자 동작중", menu)
            self.icon.run_detached()
            
            # 업데이트 후 재시작이었다면 성공 팝업 띄우기
            if getattr(self, '_just_updated', False):
                self._just_updated = False
                self.root.after(2000, self._show_update_success_popup)
        except Exception as e:
            print(f"트레이 아이콘 생성 실패 (시도 {attempt + 1}): {e}")
            self.icon = None
            if attempt < MAX_RETRIES:
                self.root.after(3000, lambda: self._create_tray_icon_with_retry(attempt + 1))

    def hide_window(self):
        self.root.withdraw()
        if getattr(self, 'settings_win', None) and self.settings_win.winfo_exists():
            self.settings_win.destroy()
        if not self.icon:
            self._create_tray_icon_with_retry()

    def _prompt_password(self):
        if getattr(self, '_is_prompting', False): return
        self._is_prompting = True

        pwd_win = ctk.CTkToplevel()
        pwd_win.title("보안 잠금")
        pwd_win.geometry("200x300")
        pwd_win.resizable(False, False)
        pwd_win.attributes('-topmost', True)
        pwd_win.grab_set()
        
        def on_close():
            self._is_prompting = False
            pwd_win.destroy()
        pwd_win.protocol("WM_DELETE_WINDOW", on_close)
        pwd_win.bind("<Key>", lambda e: "break")
        
        ctk.CTkLabel(pwd_win, text="비밀번호 입력", font=ctk.CTkFont(family=self.font_family, size=11)).pack(pady=(15, 5))
        display_var = ctk.StringVar(value="")
        lbl = ctk.CTkLabel(pwd_win, textvariable=display_var, font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), width=90, height=35, corner_radius=8, fg_color=("gray85", "gray20"))
        lbl.pack(pady=5)
        
        def check_pwd():
            if not pwd_win.winfo_exists(): return
            if display_var.get() == "1235":
                self._is_prompting = False
                pwd_win.destroy()
                if self.icon:
                    self.icon.stop()
                    self.icon = None
                self.root.deiconify()
            else:
                messagebox.showerror("오류", "비밀번호가 틀렸습니다.", parent=pwd_win)
                display_var.set("")
                
        def btn_click(num):
            current = display_var.get()
            if len(current) < 4:
                new_val = current + str(num)
                display_var.set(new_val)
                if len(new_val) == 4: pwd_win.after(100, check_pwd)
                
        pad_frame = ctk.CTkFrame(pwd_win, fg_color="transparent")
        pad_frame.pack(pady=5)
        buttons = ['1','2','3','4','5','6','7','8','9','C','0','']
        row = 0; col = 0
        for btn in buttons:
            if btn == 'C':
                cmd = lambda: display_var.set("")
                color = "#E74C3C"
                hover = "#C0392B"
            elif btn == '':
                col += 1
                if col > 2: col = 0; row += 1
                continue
            else:
                cmd = lambda n=btn: btn_click(n)
                color = ["#3B8ED0", "#1F6AA5"]
                hover = ["#36719F", "#144870"]
            btn_widget = ctk.CTkButton(pad_frame, text=btn, font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), width=40, height=40, corner_radius=20, command=cmd)
            if btn == 'C': btn_widget.configure(fg_color=color, hover_color=hover)
            btn_widget.grid(row=row, column=col, padx=4, pady=4)
            col += 1
            if col > 2: col = 0; row += 1

    def show_window(self, icon=None, item=None):
        self.root.after(0, self._prompt_password)

    def quit_app(self, icon=None, item=None):
        self.is_running = False
        try:
            if self.icon:
                self.icon.stop()
        except:
            pass
            
        # 메인 스레드에서 안전하게 종료하기 위해 root.after 사용
        def force_exit():
            try:
                self.root.destroy()
            except:
                pass
            # 데몬 스레드들이 남아있을 수 있으므로 프로세스 강제 종료로 확실히 마무리
            os._exit(0)
            
        self.root.after(100, force_exit)

    def create_image(self, width, height):
        # 완전히 투명한 이미지 반환
        return Image.new('RGBA', (width, height), (0, 0, 0, 0))

    def get_next_event(self):
        if self.skip_today_var.get(): return "skip", None
            
        try: minutes_off = int(self.minutes_var.get())
        except: minutes_off = 0
            
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        next_time = None
        next_action = "시스템 종료"
        
        for i in range(8):
            check_date = now + timedelta(days=i)
            day_str = DAYS[check_date.weekday()]
            
            for class_name, schedule_time in TIMETABLE.items():
                if class_name in self.vars[day_str] and self.vars[day_str][class_name]["enabled"].get():
                    target_dt = datetime.strptime(schedule_time, "%H:%M")
                    target_dt = target_dt - timedelta(minutes=minutes_off)
                    target_datetime = datetime(check_date.year, check_date.month, check_date.day, target_dt.hour, target_dt.minute)
                    
                    if target_datetime > now:
                        if target_datetime.strftime("%Y-%m-%d %H:%M") in self.skipped_events: continue
                        if next_time is None or target_datetime < next_time:
                            next_time = target_datetime
                            next_action = self.vars[day_str][class_name]["action"].get()
                            

        return next_time, next_action

    def update_status_info(self):
        next_time, next_action = self.get_next_event()
        now = datetime.now()
        
        if getattr(self, 'pending_shutdown', False):
            target = getattr(self, 'pending_shutdown_target', now)
            diff = target - now
            secs = int(diff.total_seconds())
            if secs < 0: secs = 0
            status_text = f"곧 {getattr(self, 'pending_action', '시스템 종료')}됩니다! ({secs}초 남음)"
            tooltip_text = f"스마트 예약 작동중\n{status_text}"
            detail_text = "예약된 제어가 곧 실행됩니다."

        elif next_time == "skip":
            status_text = "오늘 하루 알림 끄기 켜짐"
            tooltip_text = "스마트 전원 관리자\n(오늘 하루 끄기 활성화됨)"
            detail_text = "오늘은 스케줄이 작동하지 않습니다."
        elif next_time:
            diff = next_time - now
            if diff.total_seconds() < 0: diff = timedelta(seconds=0)
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            days = diff.days
            
            if days > 0: time_left_str = f"{days}일 {hours:02d}:{minutes:02d}:{seconds:02d} 남음"
            else: time_left_str = f"{hours:02d}:{minutes:02d}:{seconds:02d} 남음"
                

            status_text = f"다음: {next_time.strftime('%H:%M')} [{next_action}]"
            detail_text = time_left_str
            if days == 0: tooltip_text = f"스마트 전원 관리자\n다음: 오늘 {next_time.strftime('%H:%M')} [{next_action}]\n{time_left_str}"
            else: tooltip_text = f"스마트 전원 관리자\n다음: {DAYS[next_time.weekday()]}요일 {next_time.strftime('%H:%M')} [{next_action}]\n{time_left_str}"
        else:
            status_text = "예약된 일정이 없습니다."
            detail_text = "설정창에서 스케줄을 추가해주세요."
            tooltip_text = "스마트 전원 관리자\n예약된 일정이 없습니다."
            
        if hasattr(self, 'countdown_var'):
            try: 
                self.root.after(0, lambda: self.countdown_var.set(status_text))
                self.root.after(0, lambda: self.status_detail_var.set(detail_text))
            except Exception: pass
            
        if self.icon: self.icon.title = tooltip_text

    def show_toast_popup(self, title, message, duration, action):
        if hasattr(self, 'toast') and self.toast and self.toast.winfo_exists(): return
            
        self.toast = ctk.CTkToplevel(self.root)
        self.toast.title(title)
        
        window_width = 400
        window_height = 220
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_cordinate = screen_width - window_width - 20
        y_cordinate = screen_height - window_height - 60
        
        self.toast.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        self.toast.attributes('-topmost', True)
        self.toast.overrideredirect(True)
        
        frame = ctk.CTkFrame(self.toast, fg_color=("white", "gray10"), corner_radius=15, border_width=2, border_color="#3498DB")
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        lbl_title = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(family=self.font_family, size=18, weight="bold"), text_color="#3498DB")
        lbl_title.pack(pady=(20, 5))
        
        lbl_msg = ctk.CTkLabel(frame, text=message, font=ctk.CTkFont(family=self.font_family, size=13), wraplength=360)
        lbl_msg.pack(pady=(0, 15))
        
        self.toast_time_left = duration
        lbl_time = ctk.CTkLabel(frame, text=f"{self.toast_time_left}초 후 {action} 실행", font=ctk.CTkFont(family=self.font_family, size=24, weight="bold"), text_color="#E74C3C")
        lbl_time.pack()
        
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        def on_cancel():
            self.pending_shutdown = False
            if self.toast and self.toast.winfo_exists(): self.toast.destroy()
            if self.icon: self.icon.notify("사용자의 요청으로 제어가 취소되었습니다.", "취소 완료")
                
        def on_snooze():
            self.pending_shutdown = False
            if self.toast and self.toast.winfo_exists(): self.toast.destroy()
            self.snooze_target = datetime.now() + timedelta(minutes=10)
            self.snooze_action = action
            if self.icon: self.icon.notify("10분 뒤에 다시 확인합니다.", "연기 완료")
        
        cancel_btn = ctk.CTkButton(btn_frame, text="종료 취소", fg_color="#E74C3C", hover_color="#C0392B", command=on_cancel, width=120, height=35, font=ctk.CTkFont(family=self.font_family, size=14, weight="bold"))
        cancel_btn.pack(side="left", padx=10)
        
        snooze_btn = ctk.CTkButton(btn_frame, text="10분 연기 (Snooze)", command=on_snooze, width=150, height=35, font=ctk.CTkFont(family=self.font_family, size=14, weight="bold"))
        snooze_btn.pack(side="left", padx=10)
            
        def update_timer():
            if not self.toast or not self.toast.winfo_exists(): return
                
            if not getattr(self, 'pending_shutdown', False):
                self.toast.destroy()
                return
                    
            self.toast_time_left -= 1
            if self.toast_time_left <= 0:
                pass
            else:
                lbl_time.configure(text=f"{self.toast_time_left}초 후 {action} 실행")
                self.toast.after(1000, update_timer)
                
        self.toast.after(1000, update_timer)

    def monitor_time(self):
        last_tooltip_update = 0
        if HAS_PYCAW:
            try:
                import comtypes
                comtypes.CoInitialize()
            except Exception: pass
        
        while self.is_running:
            now = datetime.now()
            current_hm = now.strftime("%H:%M")
            current_date = now.strftime("%Y-%m-%d")
            
            if time.time() - last_tooltip_update > 1:
                self.update_status_info()
                last_tooltip_update = time.time()
            
            if getattr(self, 'pending_shutdown', False):
                if getattr(self, 'pending_shutdown_target', None) and now >= self.pending_shutdown_target:
                    self.pending_shutdown = False
                    action = getattr(self, 'pending_action', "시스템 종료")
                    if action == "시스템 종료": os.system('shutdown /s /t 0')
                    elif action == "절전 모드": os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
                time.sleep(1)
                continue
                
            if getattr(self, 'snooze_target', None) and now >= self.snooze_target:
                self.snooze_target = None
                action = getattr(self, 'snooze_action', "시스템 종료")
                self.pending_shutdown = True
                self.pending_shutdown_target = now + timedelta(minutes=1)
                self.pending_action = action
                if self.show_popup_var.get():
                    self.root.after(0, lambda a=action: self.show_toast_popup("연기된 스마트 알림", "연기했던 일정에 따라 잠시 후 제어가 시작됩니다.", 60, a))
            
            if self.skip_today_var.get():
                time.sleep(5)
                continue
                
            day_index = now.weekday()
            current_day_str = DAYS[day_index]
            

            try: minutes_off = int(self.minutes_var.get())
            except ValueError: minutes_off = 0
                
            if self.last_triggered_time != current_hm:
                for class_name, schedule_time in TIMETABLE.items():
                    if class_name in self.vars[current_day_str] and self.vars[current_day_str][class_name]["enabled"].get():
                        target_dt = datetime.strptime(schedule_time, "%H:%M")
                        target_dt = target_dt - timedelta(minutes=minutes_off)
                        target_hm = target_dt.strftime("%H:%M")
                        
                        if current_hm == target_hm and not getattr(self, 'pending_shutdown', False):
                            if target_dt.strftime("%Y-%m-%d %H:%M") in self.skipped_events:
                                continue
                                
                            self.last_triggered_time = current_hm
                            action = self.vars[current_day_str][class_name]["action"].get()
                            self.pending_shutdown = True
                            self.pending_shutdown_target = now + timedelta(minutes=1)
                            self.pending_action = action
                            
                            if self.show_popup_var.get():
                                self.root.after(0, lambda a=action: self.show_toast_popup("스마트 스케줄 알림", "예약된 스마트 일정에 따라 잠시 후 제어가 시작됩니다.", 60, a))
                            
                            break
            time.sleep(1)

if __name__ == "__main__":

    mutex_name = "Global\\AutoShutdownAppV2_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:
        import tkinter.messagebox
        tkinter.messagebox.showinfo("알림", "프로그램이 이미 실행 중입니다.\n작업 표시줄 우측 하단의 숨겨진 아이콘(^)을 확인해주세요.")
        sys.exit(0)

    root = ctk.CTk()
    app = AutoShutdownAppV2(root)
    root.after(0, app.hide_window)
    root.mainloop()
