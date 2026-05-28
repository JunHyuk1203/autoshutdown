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
import ssl

# 전역 앱 인스턴스 (http_poller_thread 등에서 참조)
app_instance = None

# PyInstaller 환경 변수 오염(init.tcl) 방지 패치
# 업데이트 후 부모 프로세스의 환경변수가 상속되면 삭제된 임시 폴더를 참조하므로
# 항상 현재 _MEIPASS 기준으로 강제 재설정
if getattr(sys, 'frozen', False):
    # console=False 일 때 sys.stdout/err가 None이 되어 발생하는 AttributeError 방지 및 로그 저장
    class NullWriter:
        def __init__(self):
            self.encoding = 'utf-8'
            self.errors = 'strict'
        def write(self, text):
            try:
                # AppData 폴더 또는 실행 파일 위치에 stdout_stderr.log 기록
                with open(os.path.join(os.path.dirname(sys.executable), 'stdout_stderr.log'), 'a', encoding='utf-8') as f:
                    f.write(text)
            except:
                pass
        def flush(self): pass
        def isatty(self): return False
        def fileno(self): return -1
    sys.stdout = NullWriter()
    sys.stderr = NullWriter()

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

CURRENT_VERSION = "1.1.69"

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

def get_pc_id():
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "PC"
    
    # 영문, 숫자, 하이픈(-) 제외한 모든 문자(한글, 공백, 특수문자 등) 제거하여 URL 안전성 확보
    import re
    cleaned_hostname = re.sub(r'[^a-zA-Z0-9\-]', '', hostname)
    if not cleaned_hostname or cleaned_hostname.strip('-') == '':
        cleaned_hostname = "PC"
    
    # MAC 주소의 하위 6자리를 붙여 고유성 보장 (동일 호스트명 중복 방지)
    try:
        import uuid
        mac = uuid.getnode()
        mac_hex = f"{mac:012x}"[-6:]
    except Exception:
        mac_hex = "000000"
    return f"{cleaned_hostname}_{mac_hex}"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def sanitize_rtdb_keys(data):
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            new_key = k
            if isinstance(k, str):
                for char in [".", "$", "#", "[", "]", "/"]:
                    new_key = new_key.replace(char, "_")
            new_data[new_key] = sanitize_rtdb_keys(v)
        return new_data
    elif isinstance(data, list):
        return [sanitize_rtdb_keys(x) for x in data]
    return data

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
        self.last_applied_autostart = self.config.get("autostart", False)
        self.minutes_var = ctk.StringVar(value=str(self.config.get("minutes_before", 2)))
        self.skip_today_var = ctk.BooleanVar(value=(self.config.get("skip_date") == datetime.now().strftime("%Y-%m-%d")))
        
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
        
        self.main_tabview = ctk.CTkTabview(self.root)
        self.main_tabview.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.dash_frame = self.main_tabview.add("메인 화면")
        self.alert_frame = self.main_tabview.add("시스템 알림")
        
        self.alert_textbox = ctk.CTkTextbox(self.alert_frame, font=ctk.CTkFont(family=self.font_family, size=11), state="disabled")
        self.alert_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        title_lbl = ctk.CTkLabel(self.dash_frame, text=f"스마트 전원 관리자 (v{CURRENT_VERSION})", font=ctk.CTkFont(family=self.font_family, size=16, weight="bold"))
        title_lbl.pack(pady=(0, 5))
        
        url_lbl = ctk.CTkLabel(self.dash_frame, text="🌐 Firebase 원격 제어 작동 중", font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"), text_color="#2ECC71")
        url_lbl.pack(pady=(0, 10))
        
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
        self._is_reloading = False
        self.api_key_error_shown = False
        self.snooze_target = None
        self.snooze_action = "시스템 종료"
        self.last_all_cmd_ts = 0
        
        global app_instance
        app_instance = self
        
        # on 폴더 자동 생성 (초기세팅 모드용)
        try:
            os.makedirs(os.path.join(application_path, 'on'), exist_ok=True)
        except Exception:
            pass
        
        threading.Thread(target=self.monitor_time, daemon=True).start()
        threading.Thread(target=self.check_for_updates, daemon=True).start()
        threading.Thread(target=self.http_poller_thread, daemon=True).start()
            
        today = datetime.today()
        monday_str = (today - timedelta(days=today.weekday())).strftime("%Y%m%d")
        if self.school_info and monday_str not in self.timetable_cache:
            threading.Thread(target=self.update_timetable_background, daemon=True).start()
        else:
            self.root.after(0, self.update_timetable_ui)
        
    def add_system_alert(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.alert_textbox.configure(state="normal")
            self.alert_textbox.insert("0.0", f"[{timestamp}] {message}\n\n")
            self.alert_textbox.configure(state="disabled")
        except:
            pass



    def reload_config_from_web(self, data):
        """Firebase에서 원격 설정 변경 시 tkinter 변수 업데이트"""
        try:
            self._is_reloading = True
            
            # 먼저 CONFIG_FILE에 저장된 최신 전체 설정을 로드하여 school_code 유실 방지
            self.config = self.load_config()
            
            if 'school_info' in data:
                old_info = getattr(self, 'school_info', {})
                self.school_info = self.config.get('school_info', {})
                
                name = self.school_info.get("name", "")
                office = self.school_info.get("office_code", "")
                
                # school_code가 유실되었거나 학교명/교육청코드가 변경된 경우 자동으로 NEIS API를 통해 복구/갱신
                if name and office and (not self.school_info.get("school_code") or 
                                       old_info.get("name") != name or 
                                       old_info.get("office_code") != office):
                    def auto_resolve_school_code():
                        try:
                            url = f"https://open.neis.go.kr/hub/schoolInfo?Type=json&pIndex=1&pSize=5&ATPT_OFCDC_SC_CODE={office}&SCHUL_NM={urllib.parse.quote(name)}"
                            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=5) as res:
                                res_data = json.loads(res.read().decode('utf-8'))
                                if "schoolInfo" in res_data:
                                    row = res_data["schoolInfo"][1]["row"][0]
                                    self.school_info["school_code"] = row["SD_SCHUL_CODE"]
                                    self.school_info["school_kind"] = row["SCHUL_KND_SC_NM"]
                                    self.config["school_info"] = self.school_info
                                    self.save_config()
                        except Exception as ex:
                            try:
                                with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                    ef.write(f"[{datetime.now()}] auto_resolve_school_code error: {ex}\n")
                            except: pass
                        
                        # 복구/갱신 완료 후 시간표 및 급식 정보 다시 가져오기
                        self.timetable_cache = {}
                        self.meal_cache = {}
                        self.root.after(0, lambda: self.timetable_label.configure(text="시간표 정보를 불러오는 중...") if hasattr(self, 'timetable_label') and self.timetable_label.winfo_exists() else None)
                        self.root.after(0, lambda: self.meal_label.configure(text="급식 정보를 불러오는 중...") if hasattr(self, 'meal_label') and self.meal_label.winfo_exists() else None)
                        threading.Thread(target=self.update_timetable_background, daemon=True).start()
                        
                    threading.Thread(target=auto_resolve_school_code, daemon=True).start()
                else:
                    # 정보가 같거나 단순 학년/반/API키 변경 시 일반 시간표 업데이트 수행
                    if (old_info.get('grade') != self.school_info.get('grade') or
                        old_info.get('class_nm') != self.school_info.get('class_nm') or
                        old_info.get('api_key') != self.school_info.get('api_key')):
                        
                        self.timetable_cache = {}
                        self.meal_cache = {}
                        if hasattr(self, 'timetable_label') and self.timetable_label.winfo_exists():
                            self.timetable_label.configure(text="시간표 정보를 불러오는 중...")
                        if hasattr(self, 'meal_label') and self.meal_label.winfo_exists():
                            self.meal_label.configure(text="급식 정보를 불러오는 중...")
                            
                        threading.Thread(target=self.update_timetable_background, daemon=True).start()
                
                # GUI 학교명 라벨 갱신
                if hasattr(self, 'lbl_school') and self.lbl_school.winfo_exists():
                    school_name = self.school_info.get("name", "학교 미설정")
                    grade = self.school_info.get("grade", "")
                    class_nm = self.school_info.get("class_nm", "")
                    self.lbl_school.configure(text=f"{school_name} {grade}학년 {class_nm}반" if grade else school_name)

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

        except Exception as e:
            self._is_reloading = False
            try:
                with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                    ef.write(f"[{datetime.now()}] reload_config_from_web FAILED: {e}\n")
            except: pass



    def http_poller_thread(self):
        while self.is_running:
            central_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/"
            try:
                pc_id = get_pc_id()
                    
                next_time, next_action = self.get_next_event()
                if next_time and next_time != "skip":
                    date_diff = (next_time.date() - datetime.now().date()).days
                    if date_diff == 0: day_prefix = "오늘 "
                    elif date_diff == 1: day_prefix = "내일 "
                    else: day_prefix = f"{DAYS[next_time.weekday()]}요일 "
                    next_str = f"{day_prefix}{next_time.strftime('%H:%M')} [{next_action}]"
                else:
                    next_str = "오늘 안 함" if next_time == "skip" else "없음"
                
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        current_cfg = sanitize_rtdb_keys(json.load(f))
                except: current_cfg = {}
                
                ip = get_local_ip()
                ssl_context = ssl._create_unverified_context()
                
                try:
                    current_user = os.getlogin()
                except Exception:
                    current_user = os.environ.get('USERNAME') or 'SYSTEM'
                
                # 1. 내 PC 상태 보고 (PATCH)
                status_payload = json.dumps({
                    'ip': ip,
                    'hostname': socket.gethostname(),
                    'user': current_user,
                    'version': CURRENT_VERSION,
                    'status': 'online',
                    'next_event': next_str,
                    'last_seen': datetime.now().strftime('%H:%M:%S'),
                    'last_seen_ts': {'.sv': 'timestamp'},
                    'config': current_cfg
                }).encode('utf-8')
                
                patch_url = f"{central_url.rstrip('/')}/pcs/{pc_id}.json"
                patch_req = urllib.request.Request(
                    patch_url, 
                    data=status_payload, 
                    method='PUT', 
                    headers={
                        'Content-Type': 'application/json',
                        'Content-Length': str(len(status_payload))
                    }
                )
                try:
                    with urllib.request.urlopen(patch_req, timeout=10, context=ssl_context) as res:
                        pass
                except urllib.error.HTTPError as he:
                    try:
                        err_body = he.read().decode('utf-8', errors='replace')
                        with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                            ef.write(f"[{datetime.now()}] PUT error: {he.code} {he.reason} | URL: {patch_url} | Body: {err_body}\n")
                    except: pass
                except Exception as e:
                    try:
                        with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                            ef.write(f"[{datetime.now()}] PUT error: {e}\n")
                    except: pass
                
                # 2. 다른 PC 목록 가져오기 (비활성화 - Firebase 직접 연동)
                
                # 3. 대기 중인 명령 확인 (GET)
                cmd = None
                cmd_type = None
                
                # 개별 명령 조회
                cmd_url = f"{central_url.rstrip('/')}/commands/{pc_id}.json"
                cmd_req = urllib.request.Request(cmd_url, method='GET')
                try:
                    with urllib.request.urlopen(cmd_req, timeout=6, context=ssl_context) as res:
                        cmd = json.loads(res.read().decode('utf-8'))
                        if cmd:
                            cmd_type = 'individual'
                except Exception as e:
                    try:
                        with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                            ef.write(f"[{datetime.now()}] GET cmd error: {e}\n")
                    except: pass
                        
                # 개별 명령이 없으면 전체 명령 조회
                if not cmd:
                    all_cmd_url = f"{central_url.rstrip('/')}/commands/__ALL__.json"
                    all_cmd_req = urllib.request.Request(all_cmd_url, method='GET')
                    try:
                        with urllib.request.urlopen(all_cmd_req, timeout=6, context=ssl_context) as res:
                            cmd = json.loads(res.read().decode('utf-8'))
                            if cmd:
                                cmd_type = 'all'
                                cmd_ts = cmd.get('timestamp', 0)
                                # 이미 처리한 전체 명령이거나 8초 이상 지난 오래된 명령이면 무시
                                if cmd_ts == getattr(self, 'last_all_cmd_ts', 0) or time.time() - cmd_ts > 8.0:
                                    cmd = None
                                else:
                                    # 유효한 전체 명령이므로 중복 실행을 막기 위해 타임스탬프 기록
                                    self.last_all_cmd_ts = cmd_ts
                    except Exception as e:
                        try:
                            with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                ef.write(f"[{datetime.now()}] GET all cmd error: {e}\n")
                        except: pass
                                
                # 명령 실행
                if cmd and isinstance(cmd, dict):
                    action = cmd.get("action")
                    message = cmd.get("message", "")
                    
                    # 진단 로그: 명령 수신 기록
                    try:
                        with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                            ef.write(f"[{datetime.now()}] CMD RECEIVED: action={action}, type={cmd_type}, msg_type={type(message).__name__}, msg_keys={list(message.keys()) if isinstance(message, dict) else 'N/A'}\n")
                    except: pass
                    
                    # 명령 실행 액션 (성공 후에 삭제)
                    cmd_success = False
                    if action == 'shutdown':
                        os.system('shutdown /s /t 0')
                        cmd_success = True
                    elif action == 'sleep':
                        os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
                        cmd_success = True
                    elif action == 'restart':
                        os.system('shutdown /r /t 0')
                        cmd_success = True
                    elif action == 'update':
                        threading.Thread(target=self.check_for_updates, kwargs={'silent': True}, daemon=True).start()
                        cmd_success = True
                    elif action == 'setup_mode':
                        threading.Thread(target=self.run_setup_mode, daemon=True).start()
                        cmd_success = True
                    elif action == 'set_config' and isinstance(message, dict):
                        try:
                            current = {}
                            if os.path.exists(CONFIG_FILE):
                                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                                    current = json.load(f)
                                    
                            # 복구된 설정을 GUI 릴로드에도 적용하기 위해 message_clean 딕셔너리 생성
                            message_clean = {}
                            for k, v in message.items():
                                # 요일 스케줄 데이터 처리 (Firebase 우회용 언더바를 원래 슬래시로 De-sanitize 복구)
                                if k in DAYS and isinstance(v, dict):
                                    if k not in current:
                                        current[k] = {}
                                    message_clean[k] = {}
                                    for period, p_data in v.items():
                                        orig_period = period.replace("_", "/") # '방과후_기타' -> '방과후/기타'
                                        current[k][orig_period] = p_data
                                        message_clean[k][orig_period] = p_data
                                else:
                                    message_clean[k] = v
                                    if isinstance(v, dict) and k in current and isinstance(current[k], dict):
                                        current[k].update(v)
                                    else:
                                        current[k] = v
                                        
                            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                                json.dump(current, f, ensure_ascii=False, indent=4)
                                
                            if app_instance:
                                app_instance.root.after(0, lambda d=message_clean: app_instance.reload_config_from_web(d))
                            
                            cmd_success = True
                            
                            # ★ 핵심 수정: set_config 성공 직후 Firebase /pcs/{pc_id}/config를 즉시 갱신
                            # 기존 로직은 다음 폴링 루프(2초 후)에서야 config를 올려 대시보드에 이전 값이 보이는 문제가 있었음
                            try:
                                updated_cfg = sanitize_rtdb_keys(current)
                                cfg_patch_payload = json.dumps({'config': updated_cfg}).encode('utf-8')
                                cfg_patch_url = f"{central_url.rstrip('/')}/pcs/{pc_id}.json"
                                cfg_patch_req = urllib.request.Request(
                                    cfg_patch_url,
                                    data=cfg_patch_payload,
                                    method='PATCH',
                                    headers={'Content-Type': 'application/json'}
                                )
                                with urllib.request.urlopen(cfg_patch_req, timeout=5, context=ssl_context) as _:
                                    pass
                            except Exception as patch_ex:
                                try:
                                    with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                        ef.write(f"[{datetime.now()}] set_config immediate PATCH failed: {patch_ex}\n")
                                except: pass
                            
                            # 진단 로그: 설정 적용 성공
                            try:
                                with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                    ef.write(f"[{datetime.now()}] set_config SUCCESS: wrote {len(message)} keys to config, scheduled GUI reload\n")
                            except: pass
                            
                            # 시스템 알림: 원격 설정 수신 알림
                            if app_instance:
                                app_instance.root.after(0, lambda: app_instance.add_system_alert("✅ 원격 설정 변경이 수신되어 적용되었습니다."))
                        except Exception as ex:
                            try:
                                with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                    ef.write(f"[{datetime.now()}] set_config FAILED: {ex}\n")
                            except: pass
                    elif action == 'open_file' and isinstance(message, dict):
                        file_path = message.get('file_path', '').strip()
                        app_path  = message.get('app_path', '').strip()
                        if file_path:
                            try:
                                if app_path:
                                    subprocess.Popen([app_path, file_path])
                                else:
                                    os.startfile(file_path)
                                cmd_success = True
                                if app_instance:
                                    app_instance.root.after(0, lambda fp=file_path: app_instance.add_system_alert(f"📂 원격 파일 열기 실행: {fp}"))
                            except Exception as open_ex:
                                try:
                                    with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                        ef.write(f"[{datetime.now()}] open_file FAILED: file={file_path!r} app={app_path!r} err={open_ex}\n")
                                except: pass
                    elif action == 'message' and message:
                        self.root.after(0, lambda m=message: messagebox.showinfo("관리자 메시지", m, parent=self.root))
                        cmd_success = True
                    
                    # 명령 처리 성공 후에만 Firebase에서 삭제 (실패 시 재시도 가능)
                    if cmd_success and cmd_type == 'individual':
                        del_url = f"{central_url.rstrip('/')}/commands/{pc_id}.json"
                        del_req = urllib.request.Request(del_url, method='DELETE')
                        try:
                            with urllib.request.urlopen(del_req, timeout=6, context=ssl_context) as res:
                                pass
                        except Exception as e:
                            try:
                                with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                    ef.write(f"[{datetime.now()}] DELETE cmd error: {e}\n")
                            except: pass
            except Exception as ge:
                try:
                    with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                        ef.write(f"[{datetime.now()}] General thread error: {ge}\n")
                except: pass
            time.sleep(2)

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

    def check_for_updates(self, silent=False):
        try:
            # 캐시 방지를 위해 타임스탬프 추가
            url = f"https://raw.githubusercontent.com/JunHyuk1203/autoshutdown/main/version.json?t={int(time.time())}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                ssl_context = ssl._create_unverified_context()
            except AttributeError:
                ssl_context = None
            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                data = json.loads(response.read().decode('utf-8'))
                remote_version = data.get("version", CURRENT_VERSION)
                download_url = data.get("download_url")
                
            if self._is_newer_version(remote_version, CURRENT_VERSION) and download_url:
                self.perform_auto_update(download_url, is_manual=False, silent=silent)
        except Exception as e:
            if not silent:
                print("업데이트 확인 실패:", e)

    def _is_newer_version(self, remote, current):
        try:
            r_parts = [int(x) for x in remote.split('.')]
            c_parts = [int(x) for x in current.split('.')]
            max_len = max(len(r_parts), len(c_parts))
            r_parts.extend([0] * (max_len - len(r_parts)))
            c_parts.extend([0] * (max_len - len(c_parts)))
            return r_parts > c_parts
        except Exception:
            return False

    def _show_update_error(self, msg):
        """업데이트 실패 알림 (메인 스레드에서 실행)"""
        def _show():
            try:
                parent = getattr(self, 'settings_win', None)
                if not parent or not parent.winfo_exists():
                    parent = self.root
                messagebox.showerror("업데이트 오류", msg, parent=parent)
            except Exception:
                pass
        self.root.after(0, _show)

    def perform_auto_update(self, download_url, is_manual=False, silent=False):
        # 저사양 PC 및 네트워크 환경에서 GUI 스레드 블로킹("응답 없음")을 방지하기 위해 백그라운드 스레드로 다운로드 수행
        threading.Thread(
            target=self._async_download_and_install,
            args=(download_url, is_manual, silent),
            daemon=True
        ).start()

    def _async_download_and_install(self, download_url, is_manual=False, silent=False):
        update_exe_path = os.path.join(application_path, "update_temp.exe")
        try:
            # 1. 새 버전 다운로드
            # 캐시 방지를 위해 다운로드 URL에도 타임스탬프 추가
            if "?" in download_url:
                no_cache_url = f"{download_url}&t={int(time.time())}"
            else:
                no_cache_url = f"{download_url}?t={int(time.time())}"
                
            req = urllib.request.Request(no_cache_url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                ssl_context = ssl._create_unverified_context()
            except AttributeError:
                ssl_context = None
                
            if is_manual:
                self.root.after(0, lambda: self._update_download_progress(0))

            with urllib.request.urlopen(req, timeout=300, context=ssl_context) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                chunks = []
                while True:
                    # 64KB 청크 단위로 분할 다운로드하여 메모리 소모를 낮추고 진행률 업데이트
                    chunk = response.read(1024 * 64)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and is_manual:
                        percent = int((downloaded / total_size) * 100)
                        self.root.after(0, lambda p=percent: self._update_download_progress(p))
                data = b"".join(chunks)
            
            # 2. 다운로드 무결성 검증 (최소 크기 체크 — 정상 exe는 수 MB 이상)
            if len(data) < 1_000_000:
                if not silent: self._show_update_error(f"다운로드된 파일이 너무 작습니다 ({len(data)} bytes).\n네트워크 오류일 수 있습니다. 다시 시도해주세요.")
                if is_manual:
                    self.root.after(0, self._restore_update_btn)
                return
            
            with open(update_exe_path, 'wb') as out_file:
                out_file.write(data)
            
            # 디스크에 기록된 파일 크기 재확인
            if os.path.getsize(update_exe_path) != len(data):
                if not silent: self._show_update_error("다운로드 파일 저장 중 오류가 발생했습니다.\n디스크 공간을 확인해주세요.")
                try: os.remove(update_exe_path)
                except: pass
                if is_manual:
                    self.root.after(0, self._restore_update_btn)
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
                    if not silent: self._show_update_error(f"실행 파일 교체에 실패했습니다.\n프로그램이 다른 곳에서 사용 중일 수 있습니다.\n\n오류: {e}")
                    if is_manual:
                        self.root.after(0, self._restore_update_btn)
                    return  # 교체 실패 시 여기서 중단 (프로그램 종료하지 않음)
                
                # 5. 파일 교체 성공 → 새 프로세스 실행
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
            if not silent: self._show_update_error(f"업데이트 중 오류가 발생했습니다.\n인터넷 연결을 확인해주세요.\n\n오류: {e}")
            if is_manual:
                self.root.after(0, self._restore_update_btn)

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

    def update_autostart_shortcut(self, enable):
        appdata = os.getenv('APPDATA')
        if not appdata: return
        startup_dir = os.path.join(appdata, r'Microsoft\Windows\Start Menu\Programs\Startup')
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
            
            # 부팅 시(로그인 전) 백그라운드 실행을 위한 작업 스케줄러 자동 등록
            if getattr(sys, 'frozen', False):
                exe_path = os.path.join(application_path, "auto_shutdown.exe")
                try:
                    # 이미 등록되어 있는지 확인
                    chk = subprocess.run(['powershell', '-Command', 'Get-ScheduledTask -TaskName "AutoShutdown_Headless"'],
                                         capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    if chk.returncode != 0:
                        # 미등록 시 관리자 권한으로 등록 시도
                        ps_cmds = (
                            f"$action = New-ScheduledTaskAction -Execute '{exe_path}' -Argument '--headless'; "
                            f"$trigger = New-ScheduledTaskTrigger -AtStartup; "
                            f"$principal = New-ScheduledTaskPrincipal -UserId 'NT AUTHORITY\\\\SYSTEM' -LogonType ServiceAccount; "
                            f"Register-ScheduledTask -TaskName 'AutoShutdown_Headless' -Action $action -Trigger $trigger -Principal $principal -Force"
                        )
                        run_cmd = f"Start-Process powershell -ArgumentList '-Command \"{ps_cmds}\"' -Verb RunAs -WindowStyle Hidden -Wait"
                        subprocess.run(['powershell', '-Command', run_cmd],
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception:
                    pass
        else:
            if os.path.exists(vbs_path): os.remove(vbs_path)
            # 작업 스케줄러 등록 해제
            try:
                subprocess.run(['powershell', '-Command', "Start-Process powershell -ArgumentList '-Command \"Unregister-ScheduledTask -TaskName ''AutoShutdown_Headless'' -Confirm:$false\"' -Verb RunAs -WindowStyle Hidden -Wait"],
                               capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception:
                pass

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
                
            autostart_val = new_config.get("autostart", False)
            if getattr(self, 'last_applied_autostart', None) != autostart_val:
                self.last_applied_autostart = autostart_val
                threading.Thread(target=self.update_autostart_shortcut, args=(autostart_val,), daemon=True).start()
                
            self.update_status_info()
        except Exception: pass


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
        self.settings_win.geometry("380x370")
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
        ctk.CTkLabel(update_card, text=f"🔑 PC 고유 ID: {get_pc_id()}", font=ctk.CTkFont(family=self.font_family, size=11), text_color="gray").pack(pady=(2, 2))
        self.update_btn = ctk.CTkButton(update_card, text="🔄 수동 업데이트 확인", command=self.manual_update_check, width=150, height=28, font=ctk.CTkFont(family=self.font_family, size=11))
        self.update_btn.pack(pady=(5, 8))

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
        # 저사양 PC에서 수동 확인 버튼을 누를 시 창이 굳는 현상 방지를 위해 UI를 비활성화하고 비동기로 체크
        if hasattr(self, 'update_btn') and self.update_btn and self.update_btn.winfo_exists():
            self.update_btn.configure(state="disabled", text="⏳ 업데이트 확인 중...")
        threading.Thread(target=self._async_manual_update_check, daemon=True).start()

    def _async_manual_update_check(self):
        try:
            # 캐시 방지를 위해 타임스탬프 추가
            url = f"https://raw.githubusercontent.com/JunHyuk1203/autoshutdown/main/version.json?t={int(time.time())}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                ssl_context = ssl._create_unverified_context()
            except AttributeError:
                ssl_context = None
            with urllib.request.urlopen(req, timeout=25, context=ssl_context) as response:
                data = json.loads(response.read().decode('utf-8'))
                remote_version = data.get("version", CURRENT_VERSION)
                download_url = data.get("download_url")
            
            # 성공 시 결과를 메인 스레드로 전달
            self.root.after(0, lambda: self._handle_update_check_result(remote_version, download_url, None))
        except Exception as e:
            # 실패 시 에러를 메인 스레드로 전달
            self.root.after(0, lambda: self._handle_update_check_result(None, None, str(e)))

    def _handle_update_check_result(self, remote_version, download_url, error_msg):
        self._restore_update_btn()
        
        if error_msg:
            messagebox.showerror("업데이트 오류", f"업데이트 확인 중 오류가 발생했습니다:\n{error_msg}", parent=getattr(self, 'settings_win', self.root))
            return
            
        if self._is_newer_version(remote_version, CURRENT_VERSION) and download_url:
            if messagebox.askyesno("업데이트 알림", f"새로운 버전(v{remote_version})이 발견되었습니다!\n지금 바로 업데이트하시겠습니까?", parent=getattr(self, 'settings_win', self.root)):
                if hasattr(self, 'update_btn') and self.update_btn and self.update_btn.winfo_exists():
                    self.update_btn.configure(state="disabled", text="📥 다운로드 준비 중...")
                self.perform_auto_update(download_url, is_manual=True)
        elif download_url:
            if messagebox.askyesno("업데이트 확인", f"현재 최신 버전(v{CURRENT_VERSION})을 사용 중입니다.\n강제로 최신 버전을 다시 다운로드하여 재설치하시겠습니까?", parent=getattr(self, 'settings_win', self.root)):
                if hasattr(self, 'update_btn') and self.update_btn and self.update_btn.winfo_exists():
                    self.update_btn.configure(state="disabled", text="📥 다운로드 준비 중...")
                self.perform_auto_update(download_url, is_manual=True)
        else:
            messagebox.showerror("업데이트 오류", "버전 정보를 불러오지 못했습니다.", parent=getattr(self, 'settings_win', self.root))

    def _update_download_progress(self, percent):
        try:
            if hasattr(self, 'update_btn') and self.update_btn and self.update_btn.winfo_exists():
                self.update_btn.configure(text=f"📥 다운로드 중 ({percent}%)...")
        except Exception:
            pass

    def _restore_update_btn(self):
        try:
            if hasattr(self, 'update_btn') and self.update_btn and self.update_btn.winfo_exists():
                self.update_btn.configure(state="normal", text="🔄 수동 업데이트 확인")
        except Exception:
            pass

    def get_tray_server_status(self, item=None):
        return "✅ Firebase 원격 제어 연동 완료"

    def cancel_shutdown(self, icon=None, item=None):
        self.pending_shutdown = False
        if self.icon: self.icon.notify("예약된 시스템 종료/절전이 취소되었습니다.", "종료 취소")

    def get_menu(self):
        menu_items = [
            pystray.MenuItem(f"버전: v{CURRENT_VERSION}", lambda icon, item: None),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("✅ Firebase 원격 제어 연동 중", lambda icon, item: None),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('오늘 하루 끄지 않기', self.toggle_skip_state, checked=self.get_skip_state),
            pystray.MenuItem('열기 (대시보드)', self.show_window),
            pystray.MenuItem('🔄 업데이트 확인', lambda icon, item: self.root.after(0, self.manual_update_check))
        ]
        menu_items.append(pystray.MenuItem('❌ 대기열에 있는 제어 강제 취소', self.cancel_shutdown, visible=lambda item: getattr(self, 'pending_shutdown', False)))
        menu_items.append(pystray.Menu.SEPARATOR)
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
        pwd_win.bind("<Key>", lambda e: "break" if e.keysym not in ('Alt_L', 'Alt_R', 'F4') else None)
        
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

    def send_offline_status(self):
        try:
            pc_id = get_pc_id()
            central_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/"
            ssl_context = ssl._create_unverified_context()
            
            offline_payload = json.dumps({
                'status': 'offline',
                'last_seen': datetime.now().strftime('%H:%M:%S'),
                'last_seen_ts': {'.sv': 'timestamp'}
            }).encode('utf-8')
            
            patch_url = f"{central_url.rstrip('/')}/pcs/{pc_id}.json"
            req = urllib.request.Request(
                patch_url,
                data=offline_payload,
                method='PATCH',
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=3, context=ssl_context) as res:
                pass
        except Exception:
            pass

    def quit_app(self, icon=None, item=None):
        self.is_running = False
        try:
            if self.icon:
                self.icon.stop()
        except:
            pass
            
        # 메인 스레드에서 안전하게 종료하기 위해 root.after 사용
        def force_exit():
            self.send_offline_status()
            try:
                self.root.destroy()
            except:
                pass
            # 데몬 스레드들이 남아있을 수 있으므로 프로세스 강제 종료로 확실히 마무리
            os._exit(0)
            
        self.root.after(100, force_exit)

    def run_setup_mode(self):
        """필수 프로세스와 파일탐색기를 제외한 모든 프로세스를 강제 종료 후 on 폴더의 프로그램을 실행"""
        self.root.after(0, lambda: self.add_system_alert("🚀 초기세팅 모드 시작 중..."))
        
        KEEP = {
            'system', 'idle', 'smss.exe', 'csrss.exe', 'wininit.exe',
            'winlogon.exe', 'services.exe', 'lsass.exe', 'svchost.exe',
            'dwm.exe', 'registry', 'memcompression', 'explorer.exe',
            'auto_shutdown.exe', 'taskmgr.exe', 'conhost.exe',
            'fontdrvhost.exe', 'spoolsv.exe', 'runtimebroker.exe',
            'sihost.exe', 'taskhostw.exe', 'ctfmon.exe', 'dllhost.exe',
            'audiodg.exe', 'python.exe', 'pythonw.exe', 'searchhost.exe',
            'startmenuexperiencehost.exe', 'shellexperiencehost.exe',
            'textinputhost.exe', 'securityhealthservice.exe',
        }
        my_pid = os.getpid()
        
        try:
            result = subprocess.run(
                ['tasklist', '/fo', 'csv', '/nh'],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in result.stdout.strip().split('\n'):
                try:
                    line = line.strip()
                    if not line: continue
                    parts = line.strip('"').split('","')
                    if len(parts) < 2: continue
                    name = parts[0].strip('"').lower()
                    pid = int(parts[1].strip('"'))
                    if pid == my_pid: continue
                    if name in KEEP: continue
                    subprocess.run(
                        ['taskkill', '/f', '/pid', str(pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                except: pass
        except Exception as e:
            self.root.after(0, lambda m=str(e): self.add_system_alert(f"⚠️ 프로세스 종료 오류: {m}"))
        
        time.sleep(1)
        
        on_folder = os.path.join(application_path, 'on')
        os.makedirs(on_folder, exist_ok=True)
        
        launched = 0
        RUNNABLE_EXTS = ('.exe', '.lnk', '.bat', '.cmd', '.vbs')
        # 우선순위: exe > lnk > bat > cmd > vbs (같은 stem이면 1개만 실행)
        EXT_PRIORITY = {'.exe': 0, '.lnk': 1, '.bat': 2, '.cmd': 3, '.vbs': 4}
        
        try:
            # 이미 실행 중인 프로세스 목록 수집
            running_procs = set()
            try:
                tl = subprocess.run(
                    ['tasklist', '/fo', 'csv', '/nh'],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                for line in tl.stdout.strip().split('\n'):
                    line = line.strip()
                    if not line: continue
                    parts = line.strip('"').split('","')
                    if parts:
                        running_procs.add(parts[0].strip('"').lower())
            except Exception:
                pass
            
            # on 폴더 파일 목록을 stem 기준으로 중복 제거 (우선순위 높은 것만 실행)
            stem_map = {}  # stem(소문자) -> (priority, filename)
            for f in os.listdir(on_folder):
                ext = os.path.splitext(f)[1].lower()
                stem = os.path.splitext(f)[0].lower()
                if ext not in EXT_PRIORITY:
                    continue
                pri = EXT_PRIORITY[ext]
                if stem not in stem_map or pri < stem_map[stem][0]:
                    stem_map[stem] = (pri, f)
            
            for stem, (pri, f) in stem_map.items():
                ext = os.path.splitext(f)[1].lower()
                # .exe의 경우 이미 실행 중이면 건너뜀
                if ext == '.exe' and f.lower() in running_procs:
                    self.root.after(0, lambda m=f: self.add_system_alert(f"⏭️ 이미 실행 중 (건너뜀): {m}"))
                    continue
                try:
                    full_path = os.path.join(on_folder, f)
                    subprocess.Popen(
                        full_path,
                        cwd=on_folder,
                        shell=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    launched += 1
                    time.sleep(0.3)  # 연속 실행 방지용 짧은 딜레이
                except Exception as e:
                    self.root.after(0, lambda m=f"{f}: {e}": self.add_system_alert(f"⚠️ 실행 실패 - {m}"))
        except Exception as e:
            self.root.after(0, lambda m=str(e): self.add_system_alert(f"⚠️ on 폴더 오류: {m}"))
        
        self.root.after(0, lambda: self.add_system_alert(f"✅ 초기세팅 완료: 창 정리 후 {launched}개 프로그램 실행됨"))

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
                    
                    if target_datetime.replace(second=0, microsecond=0) >= now.replace(second=0, microsecond=0):
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
                
            date_diff = (next_time.date() - now.date()).days
            if date_diff == 0: day_prefix = "오늘 "
            elif date_diff == 1: day_prefix = "내일 "
            else: day_prefix = f"{DAYS[next_time.weekday()]}요일 "

            status_text = f"다음: {day_prefix}{next_time.strftime('%H:%M')} [{next_action}]"
            detail_text = time_left_str
            if date_diff == 0: tooltip_text = f"스마트 전원 관리자\n다음: 오늘 {next_time.strftime('%H:%M')} [{next_action}]\n{time_left_str}"
            elif date_diff == 1: tooltip_text = f"스마트 전원 관리자\n다음: 내일 {next_time.strftime('%H:%M')} [{next_action}]\n{time_left_str}"
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
            
        if self.icon:
            full_title = tooltip_text + f"\n{self.get_tray_server_status()}"
            if len(full_title) >= 128:
                full_title = full_title[:124] + "..."
            self.icon.title = full_title
            try: self.icon.update_menu()
            except: pass

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
            
        self.toast.protocol("WM_DELETE_WINDOW", on_cancel)
        
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
                            actual_dt = datetime(now.year, now.month, now.day, target_dt.hour, target_dt.minute)
                            if actual_dt.strftime("%Y-%m-%d %H:%M") in self.skipped_events:
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

class HeadlessShutdownApp:
    def __init__(self):
        self.is_running = True
        self.skipped_events = set()
        self.last_triggered_time = None
        self.config = self.load_config()
        self.last_all_cmd_ts = 0
        
        # 백그라운드 스레드들 시작
        threading.Thread(target=self.socket_listener, daemon=True).start()
        threading.Thread(target=self.monitor_time, daemon=True).start()
        threading.Thread(target=self.http_poller_thread, daemon=True).start()
        threading.Thread(target=self.check_for_updates, daemon=True).start()
        
        # 메인 스레드 유지
        while self.is_running:
            time.sleep(1)
            
    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception: pass
        return {}
        
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception: pass

    def get_next_event(self):
        self.config = self.load_config()
        
        skip_date = self.config.get("skip_date", "")
        today_str = datetime.now().strftime("%Y-%m-%d")
        if skip_date == today_str:
            return "skip", None
            
        try: minutes_off = int(self.config.get("minutes_before", 2))
        except: minutes_off = 0
            
        now = datetime.now()
        next_time = None
        next_action = "시스템 종료"
        
        for i in range(8):
            check_date = now + timedelta(days=i)
            day_str = DAYS[check_date.weekday()]
            
            day_schedule = self.config.get(day_str, {})
            for class_name, schedule_time in TIMETABLE.items():
                class_config = day_schedule.get(class_name, {})
                
                is_enabled = False
                action_val = "시스템 종료"
                if isinstance(class_config, bool):
                    is_enabled = class_config
                elif isinstance(class_config, dict):
                    is_enabled = class_config.get("enabled", False)
                    action_val = class_config.get("action", "시스템 종료")
                    
                if is_enabled:
                    target_dt = datetime.strptime(schedule_time, "%H:%M")
                    target_dt = target_dt - timedelta(minutes=minutes_off)
                    target_datetime = datetime(check_date.year, check_date.month, check_date.day, target_dt.hour, target_dt.minute)
                    
                    if target_datetime.replace(second=0, microsecond=0) >= now.replace(second=0, microsecond=0):
                        if target_datetime.strftime("%Y-%m-%d %H:%M") in self.skipped_events:
                            continue
                        if next_time is None or target_datetime < next_time:
                            next_time = target_datetime
                            next_action = action_val
        return next_time, next_action

    def monitor_time(self):
        while self.is_running:
            now = datetime.now()
            current_hm = now.strftime("%H:%M")
            
            next_time, next_action = self.get_next_event()
            if next_time and next_time != "skip":
                if current_hm == next_time.strftime("%H:%M") and self.last_triggered_time != current_hm:
                    self.last_triggered_time = current_hm
                    if next_action == "시스템 종료":
                        os.system('shutdown /s /t 0')
                    elif next_action == "절전 모드":
                        os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
            time.sleep(1)

    def socket_listener(self):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('127.0.0.1', 19985))
            s.listen(1)
        except Exception:
            self.is_running = False
            return
            
        while self.is_running:
            try:
                s.settimeout(1.0)
                conn, addr = s.accept()
            except socket.timeout:
                continue
            except Exception:
                break
                
            try:
                data = conn.recv(1024).decode('utf-8')
                if data == "exit":
                    conn.sendall(b"ok")
                    conn.close()
                    self.is_running = False
                    break
                conn.close()
            except Exception:
                pass
        try:
            s.close()
        except:
            pass
        os._exit(0)

    def http_poller_thread(self):
        _log_path = os.path.join(application_path, 'headless_debug.log')
        def _log(msg):
            try:
                with open(_log_path, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now()}] {msg}\n")
            except: pass

        _log("headless http_poller_thread started")
        _headers = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'}

        while self.is_running:
            central_url = "https://atss-a1f9e-default-rtdb.firebaseio.com/"
            try:
                pc_id = get_pc_id()
                    
                next_time, next_action = self.get_next_event()
                if next_time and next_time != "skip":
                    date_diff = (next_time.date() - datetime.now().date()).days
                    if date_diff == 0: day_prefix = "오늘 "
                    elif date_diff == 1: day_prefix = "내일 "
                    else: day_prefix = f"{DAYS[next_time.weekday()]}요일 "
                    next_str = f"{day_prefix}{next_time.strftime('%H:%M')} [{next_action}]"
                else:
                    next_str = "오늘 안 함" if next_time == "skip" else "없음"
                
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        current_cfg = sanitize_rtdb_keys(json.load(f))
                except: current_cfg = {}
                
                ip = get_local_ip()
                ssl_context = ssl._create_unverified_context()
                
                try:
                    current_user = os.getlogin()
                except Exception:
                    current_user = os.environ.get('USERNAME') or 'SYSTEM'
                
                # 1. 상태 보고 (PUT)
                status_payload = json.dumps({
                    'ip': ip,
                    'hostname': socket.gethostname(),
                    'user': current_user,
                    'version': CURRENT_VERSION,
                    'status': 'online',
                    'next_event': next_str,
                    'last_seen': datetime.now().strftime('%H:%M:%S'),
                    'last_seen_ts': {'.sv': 'timestamp'},
                    'config': current_cfg
                }).encode('utf-8')
                
                patch_url = f"{central_url.rstrip('/')}/pcs/{pc_id}.json"
                patch_req = urllib.request.Request(
                    patch_url, 
                    data=status_payload, 
                    method='PUT', 
                    headers={
                        'Content-Type': 'application/json',
                        'Content-Length': str(len(status_payload)),
                        'User-Agent': 'Mozilla/5.0'
                    }
                )
                try:
                    with urllib.request.urlopen(patch_req, timeout=10, context=ssl_context) as res:
                        pass
                except Exception as e:
                    _log(f"PUT status error: {e}")
                
                # 2. 명령 수신 확인 (GET)
                cmd = None
                cmd_type = None
                
                cmd_url = f"{central_url.rstrip('/')}/commands/{pc_id}.json"
                cmd_req = urllib.request.Request(cmd_url, method='GET', headers={'User-Agent': 'Mozilla/5.0'})
                try:
                    with urllib.request.urlopen(cmd_req, timeout=5, context=ssl_context) as res:
                        cmd = json.loads(res.read().decode('utf-8'))
                        if cmd:
                            cmd_type = 'individual'
                            _log(f"CMD found (individual): {cmd}")
                except Exception as e:
                    _log(f"GET cmd error: {e}")
                        
                if not cmd:
                    all_cmd_url = f"{central_url.rstrip('/')}/commands/__ALL__.json"
                    all_cmd_req = urllib.request.Request(all_cmd_url, method='GET', headers={'User-Agent': 'Mozilla/5.0'})
                    try:
                        with urllib.request.urlopen(all_cmd_req, timeout=5, context=ssl_context) as res:
                            cmd = json.loads(res.read().decode('utf-8'))
                            if cmd:
                                cmd_type = 'all'
                                cmd_ts = cmd.get('timestamp', 0)
                                if cmd_ts == getattr(self, 'last_all_cmd_ts', 0) or time.time() - cmd_ts > 8.0:
                                    cmd = None
                                else:
                                    _log(f"CMD found (all): {cmd}")
                                    # 유효한 전체 명령이므로 중복 실행을 막기 위해 타임스탬프 기록
                                    self.last_all_cmd_ts = cmd_ts
                    except Exception as e:
                        _log(f"GET all cmd error: {e}")
                                
                # 3. 명령 실행
                if cmd and isinstance(cmd, dict):
                    action = cmd.get("action")
                    message = cmd.get("message", "")
                    _log(f"Executing cmd: action={action}")
                    
                    cmd_success = False
                    try:
                        if action == 'shutdown':
                            _log("Executing: shutdown /s /t 0")
                            subprocess.run(['shutdown', '/s', '/t', '0'], creationflags=subprocess.CREATE_NO_WINDOW)
                            cmd_success = True
                        elif action == 'sleep':
                            _log("Executing: sleep (SetSuspendState)")
                            subprocess.run(['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'], creationflags=subprocess.CREATE_NO_WINDOW)
                            cmd_success = True
                        elif action == 'restart':
                            _log("Executing: shutdown /r /t 0")
                            subprocess.run(['shutdown', '/r', '/t', '0'], creationflags=subprocess.CREATE_NO_WINDOW)
                            cmd_success = True
                        elif action == 'update':
                            _log("Executing: update check")
                            threading.Thread(target=self.check_for_updates, daemon=True).start()
                            cmd_success = True
                        elif action == 'setup_mode':
                            # headless 모드에서는 setup_mode 지원 불가 → 명령만 소비(삭제)
                            _log("setup_mode received in headless - acknowledging (no-op)")
                            cmd_success = True
                        elif action == 'message':
                            # headless 모드에서는 팝업 표시 불가 → 명령만 소비(삭제)
                            _log(f"message received in headless - acknowledging: {message}")
                            cmd_success = True
                        elif action == 'set_config' and isinstance(message, dict):
                            _log(f"Executing: set_config with {len(message)} keys")
                            current = self.load_config()
                            for k, v in message.items():
                                if k in DAYS and isinstance(v, dict):
                                    if k not in current:
                                        current[k] = {}
                                    for period, p_data in v.items():
                                        orig_period = period.replace("_", "/")
                                        current[k][orig_period] = p_data
                                else:
                                    if isinstance(v, dict) and k in current and isinstance(current[k], dict):
                                        current[k].update(v)
                                    else:
                                        current[k] = v
                            self.config = current
                            self.save_config()
                            cmd_success = True
                            
                            try:
                                updated_cfg = sanitize_rtdb_keys(current)
                                cfg_patch_payload = json.dumps({'config': updated_cfg}).encode('utf-8')
                                cfg_patch_url = f"{central_url.rstrip('/')}/pcs/{pc_id}.json"
                                cfg_patch_req = urllib.request.Request(
                                    cfg_patch_url,
                                    data=cfg_patch_payload,
                                    method='PATCH',
                                    headers=_headers
                                )
                                with urllib.request.urlopen(cfg_patch_req, timeout=5, context=ssl_context) as _:
                                    pass
                                _log("set_config Firebase PATCH success")
                            except Exception as pe:
                                _log(f"set_config Firebase PATCH error: {pe}")
                        else:
                            # 알 수 없는 명령도 소비하여 큐에 쌓이지 않도록 함
                            _log(f"Unknown action '{action}' - acknowledging to clear queue")
                            cmd_success = True
                    except Exception as exec_err:
                        _log(f"CMD execution error: {exec_err}")
                        cmd_success = True  # 실패해도 명령 삭제하여 무한 재시도 방지
                    
                    # 4. 명령 삭제 (개별 명령일 때만)
                    if cmd_success and cmd_type == 'individual':
                        del_url = f"{central_url.rstrip('/')}/commands/{pc_id}.json"
                        del_req = urllib.request.Request(del_url, method='DELETE', headers={'User-Agent': 'Mozilla/5.0'})
                        try:
                            with urllib.request.urlopen(del_req, timeout=5, context=ssl_context) as res:
                                pass
                            _log("CMD deleted from Firebase")
                        except Exception as de:
                            _log(f"CMD delete error: {de}")
            except Exception as ge:
                _log(f"General poller error: {ge}")
            time.sleep(2)

    def check_for_updates(self):
        try:
            url = f"https://raw.githubusercontent.com/JunHyuk1203/autoshutdown/main/version.json?t={int(time.time())}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                remote_version = data.get("version", CURRENT_VERSION)
                download_url = data.get("download_url")
                
            if self._is_newer_version(remote_version, CURRENT_VERSION) and download_url:
                self.perform_auto_update(download_url)
        except Exception:
            pass

    def _is_newer_version(self, remote, current):
        try:
            r_parts = [int(x) for x in remote.split('.')]
            c_parts = [int(x) for x in current.split('.')]
            max_len = max(len(r_parts), len(c_parts))
            r_parts.extend([0] * (max_len - len(r_parts)))
            c_parts.extend([0] * (max_len - len(c_parts)))
            return r_parts > c_parts
        except Exception:
            return False

    def perform_auto_update(self, download_url):
        update_exe_path = os.path.join(application_path, "update_temp.exe")
        try:
            if "?" in download_url:
                no_cache_url = f"{download_url}&t={int(time.time())}"
            else:
                no_cache_url = f"{download_url}?t={int(time.time())}"
                
            req = urllib.request.Request(no_cache_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=120) as response:
                data = response.read()
            
            if len(data) < 1_000_000:
                return
            
            with open(update_exe_path, 'wb') as out_file:
                out_file.write(data)
            
            current_exe = sys.executable if getattr(sys, 'frozen', False) else None
            if current_exe and current_exe.endswith('.exe'):
                old_exe_path = current_exe + ".old"
                if os.path.exists(old_exe_path):
                    try: os.remove(old_exe_path)
                    except: pass
                
                os.rename(current_exe, old_exe_path)
                os.rename(update_exe_path, current_exe)
                
                clean_env = os.environ.copy()
                keys_to_remove = [k for k in clean_env if 'MEI' in k or 'PYI' in k or 'TCL' in k or 'TK' in k]
                for k in keys_to_remove:
                    clean_env.pop(k, None)
                
                # 새 버전을 백그라운드로 즉시 실행
                subprocess.Popen(
                    [current_exe, "--headless"],
                    env=clean_env,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                )
                os._exit(0)
        except Exception:
            if os.path.exists(update_exe_path):
                try: os.remove(update_exe_path)
                except: pass

if __name__ == "__main__":
    import sys
    import os
    import traceback
    import socket
    
    # console=False 인 상태로 PyInstaller로 빌드된 경우, print()로 인한 크래시 방지 및 로그 저장
    if getattr(sys, 'frozen', False):
        class NullWriter:
            def __init__(self):
                self.encoding = 'utf-8'
                self.errors = 'strict'
            def write(self, text):
                try:
                    with open(os.path.join(os.path.dirname(sys.executable), 'stdout_stderr.log'), 'a', encoding='utf-8') as f:
                        f.write(text)
                except:
                    pass
            def flush(self): pass
            def isatty(self): return False
            def fileno(self): return -1
        sys.stdout = NullWriter()
        sys.stderr = NullWriter()
    
    # --headless 인자가 있으면 즉시 백그라운드 모드로 진입 (try/except 바깥)
    if "--headless" in sys.argv:
        # 전역 중복 방지 Mutex 체크
        ctypes.windll.kernel32.SetLastError(0)
        mutex_global = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\AutoShutdownAppV2_Mutex")
        err = ctypes.windll.kernel32.GetLastError()
        if err == 183:
            os._exit(0)  # sys.exit 대신 os._exit 사용하여 BaseException 우회
        HeadlessShutdownApp()
        os._exit(0)
        
    try:
        # 1. 세션 내 중복 실행 차단용 Local 뮤텍스부터 체크
        ctypes.windll.kernel32.SetLastError(0)
        mutex_local = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\AutoShutdownAppV2_Mutex")
        if ctypes.windll.kernel32.GetLastError() == 183:
            sys.exit(0)

        # 2. 전역 중복 실행 차단용 Global 뮤텍스 체크
        ctypes.windll.kernel32.SetLastError(0)
        mutex_global = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\AutoShutdownAppV2_Mutex")
        err = ctypes.windll.kernel32.GetLastError()
        
        if err == 183:
            # 다른 인스턴스(예: --headless)가 이미 실행 중인 경우에만 소켓 연결 시도 (바통 터치)
            # 이로써 평상시 무의미한 소켓 연결 시도로 인한 딜레이를 100% 원천 차단!
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                s.connect(('127.0.0.1', 19985))
                s.sendall(b"exit")
                s.recv(1024)
                s.close()
                
                # 백그라운드 프로세스가 종료되고 Mutex를 해제할 때까지 최대 2초간 0.05초 간격으로 폴링
                # 고정 대기 시간(0.5초) 대신 실시간 감지로 반응 속도를 극대화!
                released = False
                for _ in range(40):
                    ctypes.windll.kernel32.SetLastError(0)
                    test_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\AutoShutdownAppV2_Mutex")
                    test_err = ctypes.windll.kernel32.GetLastError()
                    if test_err != 183:
                        mutex_global = test_mutex
                        released = True
                        break
                    time.sleep(0.05)
                
                if not released:
                    sys.exit(0)
            except Exception:
                # 소켓 연결이 불가능한 경우 (실제 다른 GUI가 켜진 상태 등) 중복 실행 차단
                sys.exit(0)

        root = ctk.CTk()
        app = AutoShutdownAppV2(root)
        app_instance = app
        
        root.after(0, app.hide_window)
        root.mainloop()
    except SystemExit:
        pass  # 정상 종료 — 크래시 로그 남기지 않음
    except BaseException as e:
        try:
            with open(os.path.join(application_path, "crash_debug.log"), "w", encoding="utf-8") as f:
                f.write(f"CRASH OCCURRED: {type(e).__name__}: {e}\n")
                traceback.print_exc(file=f)
        except:
            pass
        sys.exit(1)
