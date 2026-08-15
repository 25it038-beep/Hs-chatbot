import requests

try:
    r = requests.get("http://localhost:8000/api/browser/diagnostics")
    print(f"Status: {r.status_code}")
    print("Local diagnostics:")
    print(r.json())
except Exception as e:
    print(f"Error checking local diagnostics: {e}")
