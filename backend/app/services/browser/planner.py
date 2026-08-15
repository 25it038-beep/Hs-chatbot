"""Action planner (section 3): convert an intent into the MINIMUM action set.

Each plan step maps to a BrowserAgent method and carries a human-readable
status line (emitted as streaming events, section 19).
"""

from typing import Optional

from .config import browser_config
from .intent import (
    CLICK,
    CLOSE_TAB,
    CONFIRM_ACTION,
    EXTRACT,
    NAVIGATE,
    OPEN_WEBSITE,
    PAUSE_MEDIA,
    PLAY_MEDIA,
    RESUME_MEDIA,
    SCREENSHOT,
    SCROLL,
    SEARCH_SITE,
    SEARCH_WEB,
    SKIP_MEDIA,
    SWITCH_TAB,
    TYPE,
    BrowserIntent,
    CURRENT_PAGE,
    lookup_site,
)


def _step(action: str, status: str) -> dict:
    return {"action": action, "status": status}


def build_plan(intent: BrowserIntent, current_url: Optional[str] = None) -> list[dict]:
    """Returns the ordered minimal action list for the intent."""
    steps: list[dict] = []
    i = intent.intent

    if i == CONFIRM_ACTION:
        return []

    if i in (OPEN_WEBSITE, NAVIGATE):
        steps.append(_step("open_website", f"🌐 Opening {intent.url or intent.service}..."))
        steps.append(_step("verify_navigation", "Checking the page..."))

    elif i == SEARCH_SITE:
        site_url = lookup_site(intent.service) if intent.service and intent.service != CURRENT_PAGE else None
        target = intent.service if intent.service and intent.service != CURRENT_PAGE else "this website"
        steps.append(_step("open_website", f"🌐 Opening {target}..." if site_url else f"🌐 Using the current page ({target})..."))
        if site_url:
            steps.append(_step("verify_navigation", "Checking the page..."))
        steps.append(_step("search_site", f'🔎 Searching {target} for "{intent.query}"...'))
        steps.append(_step("verify_results", "Checking results..."))

    elif i == SEARCH_WEB:
        # Fast retrieval path (section 5/17): no Selenium needed for a plain
        # web search; the chat pipeline grounds the answer in web results.
        steps.append(_step("delegate_web_search", "🔎 Using the fast web search..."))

    elif i == PLAY_MEDIA:
        service = intent.service or "spotify"
        site_url = lookup_site(service)
        steps.append(_step("open_website", f"🌐 Opening {service}..." if site_url else f"🌐 Opening {service}..."))
        if site_url:
            steps.append(_step("verify_navigation", "Checking the page..."))
        if intent.query:
            steps.append(_step("search_site", f'🔎 Searching {service} for "{intent.query}"...'))
            steps.append(_step("select_best_match", "🎵 Found it — picking the best match..."))
        steps.append(_step("play_media", "▶ Playing..."))
        steps.append(_step("verify_playback", "Verifying playback..."))

    elif i == PAUSE_MEDIA:
        steps.append(_step("pause_media", "⏸ Pausing..."))
        steps.append(_step("verify_media_state", "Checking player state..."))

    elif i == SWITCH_TAB:
        target = intent.service if intent.service != "previous" else "the previous tab"
        steps.append(_step("switch_tab", f"⇄ Switching to {target}..."))
        steps.append(_step("verify_navigation", "Checking the tab..."))

    elif i == CLOSE_TAB:
        target = intent.service if intent.service != CURRENT_PAGE else "this tab"
        steps.append(_step("close_tab", f"🗑 Closing the {target} tab..."))

    elif i == RESUME_MEDIA:
        steps.append(_step("resume_media", "▶ Resuming..."))
        steps.append(_step("verify_media_state", "Checking player state..."))

    elif i == SKIP_MEDIA:
        steps.append(_step("skip_media", "⏭ Skipping..."))
        steps.append(_step("verify_media_state", "Checking player state..."))

    elif i == SCROLL:
        steps.append(_step("scroll", f"🖱 Scrolling {intent.direction or 'down'}..."))

    elif i == SCREENSHOT:
        steps.append(_step("screenshot", "📸 Taking a screenshot..."))

    elif i == EXTRACT:
        steps.append(_step("extract", "📄 Extracting the page content..."))

    elif i == CLICK:
        steps.append(_step("click", f"🖱 Clicking {intent.target}..."))
        steps.append(_step("verify_navigation", "Checking the result..."))

    elif i == TYPE:
        steps.append(_step("type_text", f"⌨️ Typing into {intent.target or 'the page'}..."))
        if intent.target and "search" in (intent.target or "").lower():
            steps.append(_step("submit_search", "🔎 Submitting..."))

    elif i == DOWNLOAD:
        steps.append(_step("download", "⬇️ Preparing download..."))

    else:  # OTHER_BROWSER_ACTION
        steps.append(_step("open_website", "🌐 Opening the browser..."))

    return steps[: browser_config.MAX_PLAN_STEPS]
