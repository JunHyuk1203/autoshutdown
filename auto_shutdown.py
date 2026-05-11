import os
import sys
import threading
import time
import json
import urllib.request
import urllib.error
import urllib.parse
import re
from datetime import datetime, timedelta

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

CURRENT_VERSION = "1.1.20"

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
        title_lbl.pack(pady=(0, 10))
        
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
        
        threading.Thread(target=self.monitor_time, daemon=True).start()
        threading.Thread(target=self.check_for_updates, daemon=True).start()
        
        today = datetime.today()
        monday_str = (today - timedelta(days=today.weekday())).strftime("%Y%m%d")
        if self.school_info and monday_str not in self.timetable_cache:
            threading.Thread(target=self.update_timetable_background, daemon=True).start()
        else:
            self.update_timetable_ui()

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
        cache = self.fetch_this_week_timetable(
            self.school_info.get("office_code"),
            self.school_info.get("school_code"),
            self.school_info.get("school_kind"),
            self.school_info.get("grade"),
            self.school_info.get("class_nm")
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
                    return json.load(f)
        except Exception: pass
        return {}

    def save_config_callback(self, *args):
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
        menu_items = [
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
