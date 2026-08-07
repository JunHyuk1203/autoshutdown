from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

try:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--log-level=0')
    driver = webdriver.Chrome(options=options)
    
    driver.get('http://localhost:8000/index.html')
    time.sleep(2)
    
    logs = driver.get_log('browser')
    print("Browser Logs:")
    for log in logs:
        print(log)
        
    driver.quit()
except Exception as e:
    print(f"Error: {e}")
