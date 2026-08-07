import sys
import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Patch AutoShutdownApp.listen_commands_firebase (or http_poller_thread in GUI)
target_gui = """                # 1. 상태 보고 (PUT)
                
                current_vol = 50"""

replacement_gui = """                # 1. 상태 보고 (PUT) 매 5초마다만 실행하여 반응속도 최적화
                now_ts = time.time()
                if not hasattr(self, 'last_status_update'):
                    self.last_status_update = 0
                
                if now_ts - self.last_status_update >= 5.0:
                    self.last_status_update = now_ts
                    current_vol = 50"""

if target_gui in text:
    text = text.replace(target_gui, replacement_gui)

# Find the end of status PATCH block for GUI
target_gui_end = """                    except: pass
                
                # 2. 다른 PC 목록 가져오기 (비활성화 - Firebase 직접 연동)"""

replacement_gui_end = """                    except: pass
                
                # 2. 다른 PC 목록 가져오기 (비활성화 - Firebase 직접 연동)"""
# We need to indent the block between them by one tab.
# Actually, since I can just use regex to indent the block:

def indent_block(text, start_marker, end_marker):
    start_idx = text.find(start_marker)
    if start_idx == -1: return text
    end_idx = text.find(end_marker, start_idx)
    if end_idx == -1: return text
    
    # We replace start_marker with the if condition, then indent lines between start_marker+len and end_marker
    block_start = start_idx + len(start_marker)
    block_end = end_idx
    block = text[block_start:block_end]
    
    indented_block = "\n".join(["    " + line if line.strip() else line for line in block.split("\n")])
    
    return text[:block_start] + indented_block + text[block_end:]

# Let's use a simpler method.
# Just inject the time check, and replace the indentation.

import io

def fix_poller(source_code):
    lines = source_code.split('\n')
    out = []
    in_status_block = False
    indent = ""
    for line in lines:
        if "# 1. 상태 보고 (PUT)" in line or "# 1. 상태 보고(PUT) - Firebase" in line:
            indent_level = len(line) - len(line.lstrip())
            indent = " " * indent_level
            out.append(line)
            out.append(indent + "now_ts = time.time()")
            out.append(indent + "if not hasattr(self, 'last_status_update'): self.last_status_update = 0")
            out.append(indent + "if now_ts - self.last_status_update >= 5.0:")
            out.append(indent + "    self.last_status_update = now_ts")
            in_status_block = True
            continue
            
        if in_status_block:
            if "# 2. 다른 PC 목록" in line or "# 2. 명령 수신 확인" in line or "cmd =" in line and "None" in line:
                in_status_block = False
                out.append(line)
                continue
            
            if line.strip() == "":
                out.append(line)
            else:
                out.append("    " + line)
        else:
            out.append(line)
    return "\n".join(out)

new_text = fix_poller(text)
new_text = new_text.replace('CURRENT_VERSION = "1.1.126"', 'CURRENT_VERSION = "1.1.127"')
new_text = new_text.replace('CURRENT_VERSION = "1.1.125"', 'CURRENT_VERSION = "1.1.127"')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(new_text)
    
with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = vtext.replace('1.1.126', '1.1.127').replace('1.1.125', '1.1.127')
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)

print("auto_shutdown.py patched for faster polling, bumped to 1.1.127")
