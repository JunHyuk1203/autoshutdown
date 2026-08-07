import sys
import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

# Fix target_hwnd to be int
def replace_hwnd_get(match):
    return "target_hwnd = message.get('hwnd')\n                            if target_hwnd:\n                                try:\n                                    target_hwnd = int(target_hwnd)\n                                except ValueError:\n                                    target_hwnd = None\n                            if target_hwnd:"

# There are multiple occurrences of:
# target_hwnd = message.get('hwnd')
# if target_hwnd:
pattern = r"target_hwnd = message\.get\('hwnd'\)\s*if target_hwnd:"
text = re.sub(pattern, "target_hwnd = message.get('hwnd')\n                            if target_hwnd:\n                                try:\n                                    target_hwnd = int(target_hwnd)\n                                except ValueError:\n                                    target_hwnd = None\n                            if target_hwnd:", text)

# Fix message action
target_message_1 = """                        elif action == 'message' and message:
                            try:
                                with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                    ef.write(f"[{datetime.now()}] MESSAGE: {message}\\n")
                            except: pass
                            cmd_success = True"""

replacement_message_1 = """                        elif action == 'message' and message:
                            try:
                                with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                    ef.write(f"[{datetime.now()}] MESSAGE: {message}\\n")
                            except: pass
                            if app_instance:
                                app_instance.root.after(0, lambda m=message: messagebox.showinfo("관리자 메시지", m))
                            cmd_success = True"""
                            
if target_message_1 in text:
    text = text.replace(target_message_1, replacement_message_1)

target_message_2 = """                            elif action == 'message':
                                try:
                                    with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                        ef.write(f"[{datetime.now()}] MESSAGE: {message}\\n")
                                except: pass
                                cmd_success = True"""
                                
replacement_message_2 = """                            elif action == 'message':
                                try:
                                    with open(os.path.join(application_path, 'error.log'), 'a', encoding='utf-8') as ef:
                                        ef.write(f"[{datetime.now()}] MESSAGE: {message}\\n")
                                except: pass
                                if app_instance:
                                    app_instance.root.after(0, lambda m=message: messagebox.showinfo("관리자 메시지", m))
                                cmd_success = True"""

if target_message_2 in text:
    text = text.replace(target_message_2, replacement_message_2)

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)
print("auto_shutdown.py patched")
