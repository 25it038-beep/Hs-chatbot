import re

path = "c:/Users/BS.Harshan seliyan/OneDrive/Documents/HSBot/frontend/dist/assets/index-CKJi8abj.js"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Let's search for some recognizable parts of getBaseUrl
# For example, "VITE_API_URL" or "/api"
matches = [m.start() for m in re.finditer(r"/api", content)]
print(f"Found '/api' {len(matches)} times")

# Let's search for "hs-chatbot-2" or "onrender"
print("onrender in file:", "onrender" in content)
print("hs-chatbot-2 in file:", "hs-chatbot-2" in content)

# Find around the occurrences of /api
for idx in matches[:5]:
    start = max(0, idx - 50)
    end = min(len(content), idx + 50)
    print(f"Around idx {idx}: {repr(content[start:end])}")
