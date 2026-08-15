import requests

URL_LOGIN = "https://hs-chatbot-2.onrender.com/api/auth/login"
URL_DIAG = "https://hs-chatbot-2.onrender.com/api/browser/diagnostics"

print("Logging in to remote server...")
try:
    login_res = requests.post(URL_LOGIN, json={
        "username": "hsbot_user",
        "email": "user@hsbot.ai",
        "password": "hsbot_default_pass"
    })
    
    if login_res.status_code == 200:
        token = login_res.json().get("access_token")
        
        headers = {"Authorization": f"Bearer {token}"}
        diag_res = requests.get(URL_DIAG, headers=headers)
        print(f"Diagnostics response status: {diag_res.status_code}")
        print("Remote browser diagnostics:")
        print(diag_res.json())
    else:
        print(f"Failed to log in: {login_res.text}")
except Exception as e:
    print(f"Error checking remote diagnostics: {e}")
