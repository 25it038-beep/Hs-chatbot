import requests
import json
import sys

URL_LOGIN = "https://hs-chatbot-2.onrender.com/api/auth/login"
URL_SEND_MSG = "https://hs-chatbot-2.onrender.com/api/chats/messages"

print("Logging in to remote server...")
try:
    login_res = requests.post(URL_LOGIN, json={
        "username": "hsbot_user",
        "email": "user@hsbot.ai",
        "password": "hsbot_default_pass"
    })
    
    token = login_res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "chat_id": "ca20c921-d588-4891-8871-4460c03080e8",
        "message": "Open youtube",
        "provider": "sambanova",
        "model": "DeepSeek-V3.2"
    }
    
    print("Sending message...")
    r = requests.post(URL_SEND_MSG, headers=headers, json=payload)
    print(f"Status code: {r.status_code}")
    print("Response text:")
    print(r.text[:2000])
except Exception as e:
    print(f"Error: {e}")
