import requests
import time
import sys

TARGET_COMMIT = "8f3c041"
URL = "https://hs-chatbot-2.onrender.com/api/health"

print(f"Monitoring {URL} for commit: {TARGET_COMMIT}")
for i in range(40):
    try:
        r = requests.get(URL, timeout=10)
        data = r.json()
        current_commit = data.get("commit", "")
        print(f"[{i+1}] Current commit: {current_commit}")
        if current_commit.startswith(TARGET_COMMIT):
            print("DEPROYED SUCCESSFULLY!")
            sys.exit(0)
    except Exception as e:
        print(f"[{i+1}] Request failed: {e}")
    time.sleep(15)

print("Timeout waiting for deployment.")
sys.exit(1)
