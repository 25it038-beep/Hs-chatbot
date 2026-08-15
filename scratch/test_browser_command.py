import requests
import json
import sys

URL_LOGIN = "https://hs-chatbot-2.onrender.com/api/auth/login"
URL_CREATE_CHAT = "https://hs-chatbot-2.onrender.com/api/chats"
URL_SEND_MSG = "https://hs-chatbot-2.onrender.com/api/chats/messages"

print("Logging in to remote server...")
try:
    login_res = requests.post(URL_LOGIN, json={
        "username": "hsbot_user",
        "email": "user@hsbot.ai",
        "password": "hsbot_default_pass"
    })
    
    if login_res.status_code != 200:
        print(f"Failed to log in: {login_res.text}")
        sys.exit(1)
        
    token = login_res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a chat session
    print("Creating new chat session...")
    chat_res = requests.post(URL_CREATE_CHAT, headers=headers, json={"title": "Test Browser Control"})
    if chat_res.status_code != 200:
        print(f"Failed to create chat: {chat_res.text}")
        sys.exit(1)
        
    chat_id = chat_res.json().get("id")
    print(f"Chat created with ID: {chat_id}")
    
    # Send browser command
    payload = {
        "chat_id": chat_id,
        "message": "Open youtube",
        "provider": "sambanova",
        "model": "DeepSeek-V3.2",
        "stream": True
    }
    
    print("Sending message 'Open youtube' to stream...")
    # POST with stream=True
    r = requests.post(URL_SEND_MSG, headers=headers, json=payload, stream=True)
    print(f"Status code: {r.status_code}")
    
    for line in r.iter_lines():
        if line:
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                data_content = line_str[6:]
                if data_content == "[DONE]":
                    print("[DONE]")
                    break
                try:
                    chunk = json.loads(data_content)
                    # print type and content of chunk
                    content = chunk.get("content", "")
                    ctype = chunk.get("type", "")
                    print(f"[{ctype}] {content}")
                except Exception as e:
                    print(f"Failed to parse chunk: {line_str} ({e})")
                    
except Exception as e:
    print(f"Error: {e}")
