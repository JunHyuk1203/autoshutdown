import sys
import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Fix Headless mode
target_headless = """                # 1. 상태 보고 (PUT) 매 5초마다만 실행하여 반응속도 최적화
                now_ts = time.time()
                if not hasattr(self, 'last_status_update'): self.last_status_update = 0
                if now_ts - self.last_status_update >= 5.0:
                    self.last_status_update = now_ts
                    now_ts = time.time()
                    if not hasattr(self, 'last_status_update'):
                        self.last_status_update = 0
                
                    if now_ts - self.last_status_update >= 5.0:
                        self.last_status_update = now_ts
                        current_vol = 50"""

replacement_headless = """                # 1. 상태 보고 (PUT) 매 5초마다만 실행하여 반응속도 최적화
                now_ts = time.time()
                if not hasattr(self, 'last_status_update'): self.last_status_update = 0
                
                if now_ts - self.last_status_update >= 5.0:
                    self.last_status_update = now_ts
                    current_vol = 50"""

if target_headless in text:
    text = text.replace(target_headless, replacement_headless)

# 2. Fix GUI mode
# We need to find the status update block in GUI mode and properly indent it.
# The block starts at "# 1. 내 PC 상태 보고 (PATCH)"
# and ends right before "# 2. 다른 PC 목록 가져오기 (비활성화 - Firebase 직접 연동)"

gui_start = "                # 1. 내 PC 상태 보고 (PATCH)"
gui_end = "                # 2. 다른 PC 목록 가져오기 (비활성화 - Firebase 직접 연동)"

start_idx = text.find(gui_start)
end_idx = text.find(gui_end, start_idx)

if start_idx != -1 and end_idx != -1:
    block = text[start_idx:end_idx]
    
    # We will rewrite this block.
    # First, indent the block except the first line.
    lines = block.split('\n')
    new_lines = []
    
    # We will replace the start marker with the if condition
    new_lines.append(gui_start)
    new_lines.append("                now_ts = time.time()")
    new_lines.append("                if not hasattr(self, 'last_status_update'): self.last_status_update = 0")
    new_lines.append("                if now_ts - self.last_status_update >= 5.0:")
    new_lines.append("                    self.last_status_update = now_ts")
    
    for line in lines[1:]:
        if line.strip() == "":
            new_lines.append(line)
        else:
            new_lines.append("    " + line)
            
    new_block = '\n'.join(new_lines)
    
    text = text[:start_idx] + new_block + text[end_idx:]

text = text.replace('CURRENT_VERSION = "1.1.128"', 'CURRENT_VERSION = "1.1.129"')
text = text.replace('CURRENT_VERSION = "1.1.127"', 'CURRENT_VERSION = "1.1.129"')
text = text.replace('CURRENT_VERSION = "1.1.126"', 'CURRENT_VERSION = "1.1.129"')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = re.sub(r'1\.1\.12[0-9]', '1.1.129', vtext)
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)

print("auto_shutdown.py fully fixed, version bumped to 1.1.129")
