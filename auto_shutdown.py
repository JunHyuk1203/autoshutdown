import os
import sys
import threading
import time
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkfont
import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw
import ctypes
from ctypes import wintypes
import subprocess

CURRENT_VERSION = "1.0.9"

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
        
        # 이전 업데이트에서 남겨진 .old 파일 삭제 시도
        try:
            current_exe = sys.executable if getattr(sys, 'frozen', False) else None
            if current_exe:
                old_exe = current_exe + ".old"
                if os.path.exists(old_exe):
                    os.remove(old_exe)
        except: pass
        
        available_fonts = tkfont.families(root=self.root)
        self.font_family = "Malgun Gothic"
        for f in ["Pretendard Variable", "Pretendard", "Noto Sans KR", "NanumSquareNeo", "NanumSquare", "NanumGothic", "나눔스퀘어", "나눔고딕", "Malgun Gothic"]:
            if f in available_fonts:
                self.font_family = f
                break
                
        self.root.title(f"스마트 전원 관리자 (v{CURRENT_VERSION})")
        self.root.geometry("340x360")
        self.root.resizable(False, False)
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        self.skipped_events = set()
        self.config = self.load_config()
        self.vars = {day: {} for day in DAYS}
        
        self.global_lunch_enabled = ctk.BooleanVar(value=self.config.get("global_lunch_enabled", True))
        self.global_lunch_action = ctk.StringVar(value=self.config.get("global_lunch_action", "절전 모드"))
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
                
        self.global_lunch_enabled.trace_add('write', self.save_config_callback)
        self.global_lunch_action.trace_add('write', self.save_config_callback)
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

    def check_for_updates(self):
        try:
            url = "https://raw.githubusercontent.com/JunHyuk1203/autoshutdown/main/version.json"
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

    def perform_auto_update(self, download_url):
        try:
            update_exe_path = os.path.join(application_path, "update_temp.exe")
            req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=60) as response, open(update_exe_path, 'wb') as out_file:
                out_file.write(response.read())
                
            current_exe = sys.executable if getattr(sys, 'frozen', False) else None
            
            if current_exe and current_exe.endswith('.exe'):
                old_exe_path = current_exe + ".old"
                if os.path.exists(old_exe_path):
                    try: os.remove(old_exe_path)
                    except: pass
                
                os.rename(current_exe, old_exe_path)
                os.rename(update_exe_path, current_exe)
                
                subprocess.Popen([current_exe, "--wait-update"])
                self.quit_app()
        except Exception as e:
            print("업데이트 적용 실패:", e)

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
                "global_lunch_enabled": self.global_lunch_enabled.get(),
                "global_lunch_action": self.global_lunch_action.get(),
                "show_popup_alert": self.show_popup_var.get(),
                "skip_date": datetime.now().strftime("%Y-%m-%d") if self.skip_today_var.get() else ""
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
                script = f'Set WshShell = CreateObject("WScript.Shell")\nWshShell.Run chr(34) & "{exe_path}" & Chr(34), 0\nSet WshShell = Nothing'
            else:
                bg_script = os.path.join(application_path, "auto_shutdown.py")
                pythonw = sys.executable.replace("python.exe", "pythonw.exe")
                script = f'Set WshShell = CreateObject("WScript.Shell")\nWshShell.Run chr(34) & "{pythonw}" & Chr(34) & " " & chr(34) & "{bg_script}" & chr(34), 0\nSet WshShell = Nothing'
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
            if "점심" in next_action:
                self.skipped_events.add(datetime.now().strftime("%Y-%m-%d") + "_lunch")
                msg = "오늘 점심 감지를"
            else:
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
        ctk.CTkLabel(popup_card, text="※ 끄더라도 스케줄은 1분, 점심시간은 15초의 유예시간이\n백그라운드에서 동일하게 작동합니다.", font=ctk.CTkFont(family=self.font_family, size=10), text_color="gray").pack(pady=(0, 5))
        
        lunch_card = ctk.CTkFrame(scroll, fg_color=("#E3F2FD", "#102A43"), corner_radius=15, border_width=1, border_color="#3498DB")
        lunch_card.pack(fill="x", pady=5, ipady=5)
        ctk.CTkLabel(lunch_card, text="🍽️ 점심시간 스마트 감지 (12:30 ~ 13:10)", font=ctk.CTkFont(family=self.font_family, size=12, weight="bold")).pack(pady=(8, 2))
        
        lunch_ctrl_frame = ctk.CTkFrame(lunch_card, fg_color="transparent")
        lunch_ctrl_frame.pack(fill="x", padx=20, pady=5)
        lunch_chk = ctk.CTkSwitch(lunch_ctrl_frame, text="스마트 감지 켜기", variable=self.global_lunch_enabled, font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"), switch_width=32, switch_height=16)
        lunch_chk.pack(side="left")
        lunch_cb = ctk.CTkOptionMenu(lunch_ctrl_frame, variable=self.global_lunch_action, values=["시스템 종료", "절전 모드"], width=80, height=24, font=ctk.CTkFont(family=self.font_family, size=11))
        lunch_cb.pack(side="right")
        
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
                cb = ctk.CTkOptionMenu(row_frame, variable=var_act, values=["시스템 종료", "절전 모드"], width=70, height=24, font=ctk.CTkFont(family=self.font_family, size=11))
                cb.pack(side="right")
                
        auto_chk = ctk.CTkSwitch(scroll, text="윈도우 시작 시 백그라운드로 자동 실행", variable=self.autostart_var, font=ctk.CTkFont(family=self.font_family, size=11), switch_width=32, switch_height=16)
        auto_chk.pack(pady=(10, 5))

        update_card = ctk.CTkFrame(scroll, fg_color=("gray95", "gray15"), corner_radius=15)
        update_card.pack(fill="x", pady=5, ipady=5)
        ctk.CTkLabel(update_card, text=f"ℹ️ 현재 버전: v{CURRENT_VERSION}", font=ctk.CTkFont(family=self.font_family, size=12, weight="bold")).pack(pady=(8, 2))
        update_btn = ctk.CTkButton(update_card, text="🔄 수동 업데이트 확인", command=self.manual_update_check, width=150, height=28, font=ctk.CTkFont(family=self.font_family, size=11))
        update_btn.pack(pady=(5, 8))

    def manual_update_check(self):
        try:
            url = "https://raw.githubusercontent.com/JunHyuk1203/autoshutdown/main/version.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                remote_version = data.get("version", CURRENT_VERSION)
                download_url = data.get("download_url")
                
            if self._is_newer_version(remote_version, CURRENT_VERSION) and download_url:
                if messagebox.askyesno("업데이트 알림", f"새로운 버전(v{remote_version})이 발견되었습니다!\n지금 바로 업데이트하시겠습니까?", parent=getattr(self, 'settings_win', self.root)):
                    self.perform_auto_update(download_url)
            elif download_url:
                if messagebox.askyesno("업데이트 확인", f"현재 최신 버전(v{CURRENT_VERSION})을 사용 중입니다.\n강제로 최신 버전을 다시 다운로드하여 재설치하시겠습니까?", parent=getattr(self, 'settings_win', self.root)):
                    self.perform_auto_update(download_url)
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
        menu_items.append(pystray.MenuItem('❌ 대기열에 있는 제어 강제 취소', self.cancel_shutdown, visible=lambda item: getattr(self, 'pending_shutdown', False) or getattr(self, 'lunch_pending', False)))
        menu_items.append(pystray.MenuItem('종료', self.quit_app))
        return tuple(menu_items)

    def hide_window(self):
        self.root.withdraw()
        if getattr(self, 'settings_win', None) and self.settings_win.winfo_exists():
            self.settings_win.destroy()
        if not self.icon:
            image = self.create_image(64, 64)
            menu = pystray.Menu(self.get_menu)
            self.icon = pystray.Icon("autoshutdown_v2", image, "스마트 전원 관리자 동작중", menu)
            self.icon.run_detached()

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
        if self.icon: self.icon.stop()
        self.root.after(0, self.root.destroy)

    def create_image(self, width, height):
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, width-8, height-8), fill=(52, 152, 219))
        draw.rectangle((width//2 - 4, 15, width//2 + 4, height//2), fill=(255, 255, 255))
        return image

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
                            
            if self.global_lunch_enabled.get():
                if f"{check_date.strftime('%Y-%m-%d')}_lunch" not in self.skipped_events:
                    lunch_dt = datetime(check_date.year, check_date.month, check_date.day, 12, 30)
                    lunch_end_dt = datetime(check_date.year, check_date.month, check_date.day, 13, 10)
                    if now < lunch_end_dt:
                        target_dt_for_tooltip = lunch_dt if now < lunch_dt else now
                        if next_time is None or target_dt_for_tooltip < next_time:
                            next_time = target_dt_for_tooltip
                            lunch_act = self.global_lunch_action.get()
                            if now >= lunch_dt: next_action = f"점심 감지 작동중({lunch_act})"
                            else: next_action = f"점심 감지 대기({lunch_act})"
                            
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
        elif getattr(self, 'lunch_pending', False):
            status_text = f"미조작 감지됨! 15초 후 작동합니다."
            tooltip_text = f"스마트 점심시간 감지 작동중\n{status_text}"
            detail_text = "점심시간 미조작이 감지되어 처리 중입니다."
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
                
            if "점심" in next_action:
                status_text = f"현재 상태: {next_action}"
                detail_text = "해당 시간에 조작이 없으면 우아하게 제어됩니다."
                tooltip_text = f"스마트 전원 관리자\n{next_action}"
            else:
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

    def start_silent_lunch_grace(self, action):
        self.lunch_pending = True
        self.lunch_silent_time_left = 15
        
        def check_silent():
            if not getattr(self, 'lunch_pending', False): return
            if get_idle_time() < 1.0:
                self.lunch_pending = False
                if self.icon: self.icon.notify("마우스 움직임이 감지되어 점심시간 자동 제어가 취소되었습니다.", "우아한 취소")
                return
            
            self.lunch_silent_time_left -= 1
            if self.lunch_silent_time_left <= 0:
                self.lunch_pending = False
                if action == "시스템 종료": os.system('shutdown /s /t 0')
                elif action == "절전 모드": os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
            else:
                self.root.after(1000, check_silent)
                
        self.root.after(1000, check_silent)

    def show_toast_popup(self, title, message, duration, action, is_lunch=False):
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
            if not is_lunch: self.pending_shutdown = False
            else: self.lunch_pending = False
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
        
        if not is_lunch:
            snooze_btn = ctk.CTkButton(btn_frame, text="10분 연기 (Snooze)", command=on_snooze, width=150, height=35, font=ctk.CTkFont(family=self.font_family, size=14, weight="bold"))
            snooze_btn.pack(side="left", padx=10)
            
        if is_lunch: self.lunch_pending = True
            
        def update_timer():
            if not self.toast or not self.toast.winfo_exists(): return
                
            if is_lunch:
                if not getattr(self, 'lunch_pending', False): return
                if get_idle_time() < 1.0:
                    lbl_msg.configure(text="마우스 조작이 감지되었습니다! 작업을 계속하세요.\n(자동 제어가 취소되었습니다)", text_color="#2ECC71")
                    lbl_time.configure(text="우아한 실패(취소) 작동됨", text_color="#2ECC71")
                    cancel_btn.configure(state="disabled")
                    self.lunch_pending = False
                    self.toast.after(3000, self.toast.destroy)
                    return
            else:
                if not getattr(self, 'pending_shutdown', False):
                    self.toast.destroy()
                    return
                    
            self.toast_time_left -= 1
            if self.toast_time_left <= 0:
                if is_lunch and getattr(self, 'lunch_pending', False):
                    self.lunch_pending = False
                    lbl_time.configure(text="제어 실행 중...")
                    self.toast.update()
                    time.sleep(1)
                    self.toast.destroy()
                    if action == "시스템 종료": os.system('shutdown /s /t 0')
                    elif action == "절전 모드": os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
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
                    self.root.after(0, lambda a=action: self.show_toast_popup("연기된 스마트 알림", "연기했던 일정에 따라 잠시 후 제어가 시작됩니다.", 60, a, is_lunch=False))
            
            if self.skip_today_var.get():
                time.sleep(5)
                continue
                
            day_index = now.weekday()
            current_day_str = DAYS[day_index]
            
            if self.global_lunch_enabled.get() and not getattr(self, 'lunch_pending', False):
                if f"{current_date}_lunch" not in self.skipped_events:
                    current_t = now.time()
                    time_start = datetime.strptime("12:30", "%H:%M").time()
                    time_end = datetime.strptime("13:10", "%H:%M").time()
                    
                    if time_start <= current_t < time_end:
                        if is_media_playing(): self.last_media_time = time.time()
                        is_media_recently_played = getattr(self, 'last_media_time', 0) > time.time() - 3
                        
                        if get_idle_time() >= 90.0 and not is_media_recently_played:
                            if getattr(self, 'last_lunch_trigger_time', None) != current_hm:
                                self.last_lunch_trigger_time = current_hm
                                action = self.global_lunch_action.get()
                                if self.show_popup_var.get():
                                    self.root.after(0, lambda a=action: self.show_toast_popup("스마트 점심시간 감지", "1분 30초간 PC 미사용이 감지되었습니다.\n계속 사용중이시라면 마우스를 흔들어주세요.", 15, a, is_lunch=True))
                                else:
                                    self.start_silent_lunch_grace(action)
            
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
                                self.root.after(0, lambda a=action: self.show_toast_popup("스마트 스케줄 알림", "예약된 스마트 일정에 따라 잠시 후 제어가 시작됩니다.", 60, a, is_lunch=False))
                            
                            break
            time.sleep(1)

if __name__ == "__main__":
    import sys
    import time
    if "--wait-update" in sys.argv:
        time.sleep(3)

    mutex_name = "Global\\AutoShutdownAppV2_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183: sys.exit(0)

    root = ctk.CTk()
    app = AutoShutdownAppV2(root)
    root.after(0, app.hide_window)
    root.mainloop()
