"""Browser Automation Agent config (section 27/28).

Env-overridable knobs, retrieval/config.py style. The interactive browser is
a SEPARATE, persistent, user-visible Chrome session (not the retrieval
headless pool) so users can watch HS AI act and log into services once.
"""

import os
import sys

_ENABLED = os.getenv("BROWSER_ENABLED", "1") != "0"
# Visible by default for interactive control (section 15). Headless only when
# explicitly requested OR when there is no display (servers/CI).
if os.getenv("BROWSER_HEADLESS"):
    _HEADLESS = os.getenv("BROWSER_HEADLESS") != "0"
else:
    _HEADLESS = not sys.platform.startswith("win") and not os.environ.get("DISPLAY")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class BrowserConfig:
    BROWSER_ENABLED: bool = _ENABLED

    # Session
    BROWSER_PERSISTENT_SESSION: bool = os.getenv("BROWSER_PERSISTENT_SESSION", "1") != "0"
    # Dedicated user-data dir: user logs into services once, session persists
    # across restarts. Passwords are never typed or stored by HS AI itself.
    BROWSER_PROFILE_DIR: str = os.getenv("BROWSER_PROFILE_DIR", "./data/browser_profile")
    BROWSER_HEADLESS: bool = _HEADLESS

    # Timeouts (seconds)
    BROWSER_STARTUP_TIMEOUT_S: float = _float("BROWSER_STARTUP_TIMEOUT_S", 60.0)
    BROWSER_PAGE_LOAD_TIMEOUT_S: float = _float("BROWSER_PAGE_LOAD_TIMEOUT_S", 20.0)
    BROWSER_EXPLICIT_WAIT_S: float = _float("BROWSER_EXPLICIT_WAIT_S", 10.0)
    BROWSER_ACTION_TIMEOUT_S: float = _float("BROWSER_ACTION_TIMEOUT_S", 30.0)
    BROWSER_SEARCH_RESULTS_WAIT_S: float = _float("BROWSER_SEARCH_RESULTS_WAIT_S", 8.0)
    BROWSER_PLAYBACK_VERIFY_S: float = _float("BROWSER_PLAYBACK_VERIFY_S", 6.0)
    BROWSER_SCRIPT_TIMEOUT_S: float = _float("BROWSER_SCRIPT_TIMEOUT_S", 10.0)

    # Recovery
    MAX_ACTION_RETRIES: int = _int("MAX_ACTION_RETRIES", 2)
    MAX_PLAN_STEPS: int = _int("MAX_PLAN_STEPS", 6)

    # Safety
    # Consequential actions (buy/checkout/delete/send/pay...) require the user
    # to confirm in chat before the agent touches the page.
    BROWSER_AUTO_CONFIRM: bool = os.getenv("BROWSER_AUTO_CONFIRM", "0") != "0"
    # http(s) to localhost/private IPs: allowed only when explicitly trusted.
    BROWSER_TRUSTED_LOCAL: bool = os.getenv("BROWSER_TRUSTED_LOCAL", "0") != "0"

    # Screenshot
    BROWSER_SCREENSHOT_MAX_BYTES: int = _int("BROWSER_SCREENSHOT_MAX_BYTES", 900_000)

    # Trusted services: exact-match keys in intent.website_map
    WEBSITES = {
        "spotify": "https://open.spotify.com",
        "youtube": "https://www.youtube.com",
        "github": "https://github.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "wikipedia": "https://www.wikipedia.org",
        "stackoverflow": "https://stackoverflow.com",
        "reddit": "https://www.reddit.com",
        "x": "https://x.com",
        "twitter": "https://x.com",
        "openai": "https://openai.com",
        "netflix": "https://www.netflix.com",
        "amazon": "https://www.amazon.com",
        "linkedin": "https://www.linkedin.com",
        "facebook": "https://www.facebook.com",
        "zomato": "https://www.zomato.com",
        "swiggy": "https://www.swiggy.com",
        "instagram": "https://www.instagram.com",
        "whatsapp": "https://web.whatsapp.com",
        "telegram": "https://web.telegram.org",
        "flipkart": "https://www.flipkart.com",
        "ebay": "https://www.ebay.com",
        "maps": "https://maps.google.com",
        "google maps": "https://maps.google.com",
        "drive": "https://drive.google.com",
        "docs": "https://docs.google.com",
        "duckduckgo": "https://duckduckgo.com",
        "bing": "https://www.bing.com",
        "pinterest": "https://www.pinterest.com",
        "tumblr": "https://www.tumblr.com",
        "notion": "https://www.notion.so",
        "figma": "https://www.figma.com",
        "chatgpt": "https://chatgpt.com",
        "huggingface": "https://huggingface.co",
        "nvidia": "https://www.nvidia.com",
        "pypi": "https://pypi.org",
        "npm": "https://www.npmjs.com",
        "mdn": "https://developer.mozilla.org",
        "w3schools": "https://www.w3schools.com",
    }


browser_config = BrowserConfig()
