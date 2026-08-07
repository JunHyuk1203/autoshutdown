from playwright.sync_api import sync_playwright
import time

def check_console():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(f"Page Error: {err.message}"))
        page.on("console", lambda msg: errors.append(f"Console {msg.type}: {msg.text}") if msg.type == "error" else None)
        
        try:
            page.goto("http://localhost:8000/", timeout=10000)
            time.sleep(2)
        except Exception as e:
            print(f"Failed to load: {e}")
            
        browser.close()
        for e in errors:
            print(e)
            
check_console()
