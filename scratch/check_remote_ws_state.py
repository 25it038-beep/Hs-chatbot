import requests

URL_LOGIN = "https://hs-chatbot-2.onrender.com/api/auth/login"
URL_STATE = "https://hs-chatbot-2.onrender.com/api/browser/state"

print("Logging in to remote server...")
try:
    login_res = requests.post(URL_LOGIN, json={
        "username": "hsbot_user",
        "email": "user@hsbot.ai",
        "password": "hsbot_default_pass"
    })
    print(f"Login response status: {login_res.status_code}")
    
    if login_res.status_code == 200:
        token = login_res.json().get("access_token")
        print("Obtained token successfully.")
        
        headers = {"Authorization": f"Bearer {token}"}
        state_res = requests.get(URL_STATE, headers=headers)
        print(f"State response status: {state_res.status_code}")
        print("Remote browser state:")
        print(state_res.json())
    else:
        print(f"Failed to log in: {login_res.text}")
except Exception as e:
    print(f"Error checking remote state: {e}")
