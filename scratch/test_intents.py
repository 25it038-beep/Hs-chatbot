"""
Test intent classification for common user inputs
"""
import sys
from app.services.browser.intent import classify_browser_intent

test_messages = [
    "Open YouTube",
    "open youtube",
    "open google",
    "open youtube.com",
    "go to youtube",
    "open new tab",
    "open a tab",
    "search python on youtube",
    "play believer on spotify",
    "Open Spotify and search Daft Punk",
    "what is the weather in Paris",
]

for msg in test_messages:
    intent = classify_browser_intent(msg)
    if intent:
        print(f"'{msg}' -> INTENT={intent.intent}, service={intent.service}, query={intent.query}, url={intent.url}")
    else:
        print(f"'{msg}' -> NONE (Not detected as browser action)")
