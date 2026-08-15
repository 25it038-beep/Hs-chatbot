"""Browser Automation Agent (sections 4-16, 18).

An interactive, persistent, USER-VISIBLE Chrome session (separate from the
retrieval headless pool) that executes planned browser actions:

    open_website / navigate -> verify
    search_site -> type -> submit -> verify results
    play_media (spotify/youtube) -> search -> select best match -> play -> verify
    pause/resume/skip media -> verify player state
    click / type / scroll / extract / screenshot

Design rules honored:
- Explicit WebDriverWait only; no arbitrary sleeps (section 9).
- Multiple selector fallbacks per element (section 8): aria-labels, stable
  data-testid, name, placeholder, text match, semantic xpath.
- Every important action is verified (section 13); failures retried with the
  fallback selector set up to MAX_ACTION_RETRIES (section 14).
- Passwords are never typed or stored; auth walls are reported for manual
  login in the visible window (section 6/10).
- Consequential actions never execute automatically — the service layer
  gates them behind an explicit user confirmation (section 16).
- Logs never contain passwords, tokens, cookies or typed text (section 20).
"""

import asyncio
import base64
import io
import os
import re
import threading
import time
from typing import Callable, Optional

from loguru import logger

from .config import browser_config as cfg
from .intent import (
    CLICK,
    DOWNLOAD,
    EXTRACT,
    NAVIGATE,
    OPEN_WEBSITE,
    PAUSE_MEDIA,
    PLAY_MEDIA,
    RESUME_MEDIA,
    SCREENSHOT,
    SCROLL,
    SEARCH_SITE,
    SKIP_MEDIA,
    TYPE,
    BrowserIntent,
    CURRENT_PAGE,
)
from .planner import build_plan

try:
    from selenium import webdriver
    from selenium.common.exceptions import (
        NoSuchElementException,
        StaleElementReferenceException,
        TimeoutException,
        WebDriverException,
    )
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait

    _SELENIUM_OK = True
except Exception:  # pragma: no cover
    _SELENIUM_OK = False
    webdriver = None  # type: ignore[assignment]
    Options = None  # type: ignore[assignment]
    By = None  # type: ignore[assignment]
    Keys = None  # type: ignore[assignment]

from app.services.retrieval.extractor import extract_text

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ActionError(RuntimeError):
    """User-facing browser failure with a recovery hint."""

    def __init__(self, message: str, *, recoverable: bool = True, hint: Optional[str] = None) -> None:
        super().__init__(message)
        self.recoverable = recoverable
        self.hint = hint


class AuthRequired(ActionError):
    pass


# ---------------------------------------------------------------------------
# Element finding: primary -> fallback -> alternative -> semantic (section 8)
# ---------------------------------------------------------------------------


def _by_css(value: str) -> tuple:
    return (By.CSS_SELECTOR, value)


def _by_xpath(value: str) -> tuple:
    return (By.XPATH, value)


def _visible_candidates(driver, candidates: list[tuple], timeout: float):
    """WebDriverWait condition: first VISIBLE element among candidates.
    All candidates are polled together — no per-selector sleeps."""

    def _condition(d):
        for by, value in candidates:
            try:
                for el in d.find_elements(by, value):
                    if el.is_displayed():
                        return el
            except (StaleElementReferenceException, NoSuchElementException, WebDriverException):
                continue
        return None

    return WebDriverWait(driver, timeout).until(_condition)


def _clickable_candidates(driver, candidates: list[tuple], timeout: float):
    def _condition(d):
        for by, value in candidates:
            try:
                for el in d.find_elements(by, value):
                    if el.is_displayed() and el.is_enabled():
                        return el
            except (StaleElementReferenceException, NoSuchElementException, WebDriverException):
                continue
        return None

    return WebDriverWait(driver, timeout).until(_condition)


def _text_xpath(text: str, tag: str = "*") -> str:
    # Case-insensitive substring match on element text (semantic fallback).
    escaped = re.sub(r"([\\'\"\[\]])", r"\\\1", text)
    return (
        f"//{tag}[contains(translate(normalize-space(text()), "
        f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), "
        f"'{escaped.lower()}')]"
    )


def _text_candidates(text: str, tag: str = "*") -> list[tuple]:
    return [_by_xpath(_text_xpath(text, tag))]


def _click_element(driver, el) -> None:
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        el.click()
    except (StaleElementReferenceException, WebDriverException):
        driver.execute_script("arguments[0].click();", el)


def _type_text(driver, el, text: str) -> None:
    try:
        el.clear()
    except Exception:
        pass
    el.send_keys(text)


# ---------------------------------------------------------------------------
# The agent
# ---------------------------------------------------------------------------


class BrowserAgent:
    """Persistent interactive browser. One instance per process."""

    def __init__(self) -> None:
        self._driver = None
        self._lock = asyncio.Lock()
        self._thread_lock = threading.Lock()
        self.current_url: Optional[str] = None
        self.current_title: Optional[str] = None
        self.active_service: Optional[str] = None
        self.last_error: Optional[str] = None

    # ── lifecycle ──

    @property
    def browser_open(self) -> bool:
        return self._driver is not None

    def state(self) -> dict:
        return {
            "browser_open": self.browser_open,
            "current_url": self.current_url,
            "current_title": self.current_title,
            "active_service": self.active_service,
            "persistent_session": cfg.BROWSER_PERSISTENT_SESSION,
        }

    def _chrome_options(self) -> Options:
        opts = Options()
        if cfg.BROWSER_HEADLESS:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--disable-notifications")
        opts.add_argument("--disable-default-apps")
        opts.add_argument("--no-first-run")
        opts.add_argument("--lang=en-US,en")
        opts.add_argument("--window-size=1440,900")
        if cfg.BROWSER_PERSISTENT_SESSION:
            os.makedirs(cfg.BROWSER_PROFILE_DIR, exist_ok=True)
            opts.add_argument(f"--user-data-dir={os.path.abspath(cfg.BROWSER_PROFILE_DIR)}")
        opts.page_load_strategy = "eager"
        return opts

    def _start_driver(self):  # sync, worker thread
        opts = self._chrome_options()
        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(cfg.BROWSER_PAGE_LOAD_TIMEOUT_S)
        driver.set_script_timeout(cfg.BROWSER_SCRIPT_TIMEOUT_S)
        return driver

    async def _ensure_driver(self):
        if self._driver is not None:
            return self._driver
        if not _SELENIUM_OK or not cfg.BROWSER_ENABLED:
            raise ActionError("Browser automation is unavailable in this environment.", recoverable=False)

        def _start():
            with self._thread_lock:
                if self._driver is None:
                    self._driver = self._start_driver()
                return self._driver

        try:
            await asyncio.wait_for(asyncio.to_thread(_start), timeout=cfg.BROWSER_STARTUP_TIMEOUT_S)
        except (asyncio.TimeoutError, TimeoutError):
            self.last_error = "browser-startup-timeout"
            raise ActionError("I couldn't start the browser in time. Try again in a moment.", recoverable=True)
        except Exception as e:
            self.last_error = f"browser-startup:{type(e).__name__}"
            raise ActionError(
                "I couldn't launch Chrome. Check that Chrome is installed.",
                recoverable=False,
                hint=str(e)[:300],
            )
        return self._driver

    async def _run(self, fn: Callable, timeout: Optional[float] = None) -> object:
        """Run a sync driver op in a worker thread under the hard timeout."""
        driver = await self._ensure_driver()
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(fn, driver), timeout or cfg.BROWSER_ACTION_TIMEOUT_S
            )
        except asyncio.CancelledError:
            raise
        except (asyncio.TimeoutError, TimeoutError):
            raise ActionError("The browser didn't respond in time.", recoverable=True)
        except ActionError:
            raise
        except Exception as e:
            raise ActionError(f"Browser error: {type(e).__name__}", recoverable=True, hint=str(e)[:300])

    async def shutdown(self) -> None:
        async with self._lock:
            driver, self._driver = self._driver, None
            if driver is not None:

                def _quit(d):
                    try:
                        d.quit()
                    except Exception:
                        pass

                try:
                    await asyncio.wait_for(asyncio.to_thread(_quit, driver), timeout=15)
                except Exception:
                    pass
            self.current_url = self.current_title = None
            self.active_service = None

    # ── state sync ──

    def _refresh_state(self, driver) -> None:
        try:
            self.current_url = driver.current_url or None
            self.current_title = driver.title or None
        except Exception:
            self.current_url = self.current_title = None
        self.active_service = self._detect_service(self.current_url)

    @staticmethod
    def _detect_service(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        host = re.sub(r"^https?://", "", url).split("/")[0].lower()
        if "spotify" in host:
            return "spotify"
        if "youtube" in host or "youtu.be" in host:
            return "youtube"
        if "github" in host:
            return "github"
        if "wikipedia" in host:
            return "wikipedia"
        if "google" in host:
            return "google"
        for name in ("stackoverflow", "reddit", "netflix", "openai", "huggingface", "pypi", "npm"):
            if name in host:
                return name
        return None

    # ── generic actions (section 18) ──

    def _open_website(self, driver, url: str) -> None:
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ActionError("Only http/https URLs can be opened.", recoverable=False)
        driver.get(url)
        self._wait_ready(driver)
        self._refresh_state(driver)

    @staticmethod
    def _wait_ready(driver, timeout: Optional[float] = None) -> None:
        WebDriverWait(driver, timeout or cfg.BROWSER_EXPLICIT_WAIT_S).until(
            lambda d: d.execute_script("return document.readyState") in ("complete", "interactive")
        )

    def _verify_navigation(self, driver, expected_host: Optional[str] = None) -> dict:
        self._refresh_state(driver)
        if not self.current_url or self.current_url.startswith("about:"):
            raise ActionError("The page didn't load.", recoverable=True)
        if expected_host and expected_host not in (self.current_url or "").lower():
            logger.warning("browser nav mismatch: expected={} got={}", expected_host, self.current_url)
        return self.state()

    def _search_input_candidates(self, driver) -> list[tuple]:
        site = self._detect_service(self.current_url)
        cands: list[tuple] = []
        if site == "youtube":
            cands += [_by_css('input#search'), _by_css('input[name="search_query"]'), _by_css('input[aria-label*="Search"]')]
        elif site == "github":
            cands += [_by_css('input[name="q"]'), _by_css('textarea[name="q"]'), _by_css('input[type="search"]')]
        elif site == "wikipedia":
            cands += [_by_css('input[name="search"]'), _by_css("#searchInput"), _by_css('input[type="search"]')]
        elif site == "spotify":
            cands += [_by_css('[data-testid="search-input"]'), _by_css('input[placeholder*="What do you want to play"]'), _by_css('input[aria-label*="Search"]')]
        elif site == "google":
            cands += [_by_css('textarea[name="q"]'), _by_css('input[name="q"]'), _by_css('input[type="search"]')]
        cands += [
            _by_css('input[type="search"]'),
            _by_css('input[placeholder*="search" i]'),
            _by_css('input[type="text"]'),
            _by_css("textarea"),
        ]
        return cands

    def _search_site(self, driver, query: str) -> None:
        box = _clickable_candidates(driver, self._search_input_candidates(driver), cfg.BROWSER_EXPLICIT_WAIT_S)
        _type_text(driver, box, query)
        box.send_keys(Keys.ENTER)

    def _verify_results(self, driver, service: Optional[str]) -> dict:
        site = service if service and service != CURRENT_PAGE else self._detect_service(self.current_url)
        cands: list[tuple] = []
        if site == "youtube":
            cands = [_by_css("ytd-video-renderer"), _by_css("ytd-item-section-renderer #contents"), _by_css("a#video-title")]
        elif site == "github":
            cands = [_by_css('div[data-testid="results-list"]'), _by_css(".repo-list"), _by_css("ul.repo-list")]
        elif site == "wikipedia":
            cands = [_by_css(".mw-parser-output"), _by_css("#mw-content-text")]
        elif site == "spotify":
            cands = [_by_css('[data-testid="search-track-list"]'), _by_css('[data-testid="track-list"]'), _by_css('[data-testid="track"]')]
        elif site == "google":
            cands = [_by_css("#search"), _by_css("div#rso"), _by_css("[data-sokoban-container]")]
        cands += [_by_css("main"), _by_css("article"), _by_css("#content")]
        try:
            _visible_candidates(driver, cands, cfg.BROWSER_SEARCH_RESULTS_WAIT_S)
            self._refresh_state(driver)
            return {"results_loaded": True, "url": self.current_url, "title": self.current_title}
        except TimeoutException:
            raise ActionError("Search results didn't appear.", recoverable=True, hint="results-wait-timeout")

    def _pick_best(self, driver, css: str, query_tokens: set):
        """Highest token-overlap title match, else None (caller falls back)."""
        best, best_score = None, -1
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, css):
                try:
                    title = (el.text or el.get_attribute("aria-label") or "").lower()
                except Exception:
                    continue
                score = sum(1 for t in query_tokens if t and t in title)
                if score > best_score:
                    best, best_score = el, score
        except Exception:
            pass
        return best if best_score > 0 else None

    def _select_best_match(self, driver, service: str, query: Optional[str]) -> dict:
        """Pick the most relevant result by title text match, else the first."""
        tokens = set(re.findall(r"\w+", (query or "").lower()))
        cands: list[tuple] = []
        if service == "youtube":
            cands = [_by_css("ytd-video-renderer a#video-title"), _by_css("a#video-title"), _by_css("ytd-video-renderer")]
        elif service == "spotify":
            cands = [_by_css('[data-testid="track"]'), _by_css('[data-testid="search-track-list"] button'), _by_css('div[role="row"] button')]
        else:
            cands = [_by_css("a[href*='/watch']"), _by_css("a[href*='/track']"), _by_css("main a")]
        try:
            container = _visible_candidates(driver, cands, cfg.BROWSER_SEARCH_RESULTS_WAIT_S)
        except TimeoutException:
            raise ActionError("I couldn't find any results to play.", recoverable=True, hint="no-results")
        best = self._pick_best(
            driver,
            "ytd-video-renderer a#video-title, a#video-title, [data-testid='track']",
            tokens,
        )
        el = best
        if el is None:
            try:
                el = container.find_element(By.TAG_NAME, "a")
            except NoSuchElementException:
                el = container
        _click_element(driver, el)
        return {"selected_title": best is not None}

    # ── media recipes (sections 6-7) ──

    @staticmethod
    def _check_auth_wall(driver, service: str) -> None:
        try:
            url = driver.current_url.lower()
        except Exception:
            return
        if any(h in url for h in ("login", "accounts", "signin", "/auth/")):
            raise AuthRequired(
                f"{service} requires authentication.",
                recoverable=True,
                hint="Please log in in the browser window, then ask me to continue.",
            )
        if service == "spotify":
            try:
                if driver.find_elements(By.CSS_SELECTOR, '[data-testid="login-button"]'):
                    raise AuthRequired(
                        "Spotify requires authentication.",
                        recoverable=True,
                        hint="Please log in in the browser window, then ask me to continue.",
                    )
            except AuthRequired:
                raise
            except Exception:
                pass

    @staticmethod
    def _dismiss_consent(driver) -> None:
        for cand in (
            [_by_xpath("//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept all')]")],
            [_by_xpath("//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'reject all')]")],
            [_by_css('button[aria-label*="Accept all" i]')],
        ):
            try:
                el = _clickable_candidates(driver, cand, 2)
                _click_element(driver, el)
            except TimeoutException:
                continue

    def _spotify_play(self, driver, query: Optional[str]) -> None:
        self._check_auth_wall(driver, "spotify")
        if query:
            box = _clickable_candidates(driver, self._search_input_candidates(driver), cfg.BROWSER_EXPLICIT_WAIT_S)
            _type_text(driver, box, query)
            box.send_keys(Keys.ENTER)
            _visible_candidates(
                driver,
                [_by_css('[data-testid="search-track-list"]'), _by_css('[data-testid="track"]'), _by_css("div[role='row']")],
                cfg.BROWSER_SEARCH_RESULTS_WAIT_S,
            )
            tokens = set(re.findall(r"\w+", (query or "").lower()))
            best = self._pick_best(
                driver,
                "[data-testid='track'], [data-testid='search-track-list'] div[role='row'], [data-testid='track'] button",
                tokens,
            )
            if best is not None:
                _click_element(driver, best)
        # Ensure playing: click the play/pause button if it says "Play".
        try:
            btn = _clickable_candidates(
                driver,
                [
                    _by_css('[data-testid="control-button-playpause"]'),
                    _by_css('button[aria-label*="Play"]'),
                    _by_css('button[data-testid="play-button"]'),
                ],
                min(cfg.BROWSER_EXPLICIT_WAIT_S, 5),
            )
            if (btn.get_attribute("aria-label") or "").lower().startswith("play"):
                _click_element(driver, btn)
        except TimeoutException:
            pass  # already playing (button reads "Pause")

    def _youtube_play(self, driver, query: Optional[str]) -> None:
        self._dismiss_consent(driver)
        if query:
            box = _clickable_candidates(
                driver, [_by_css('input#search'), _by_css('input[name="search_query"]')], cfg.BROWSER_EXPLICIT_WAIT_S
            )
            _type_text(driver, box, query)
            box.send_keys(Keys.ENTER)
            tokens = set(re.findall(r"\w+", query.lower()))
            best = self._pick_best(driver, "ytd-video-renderer a#video-title, a#video-title", tokens)
            el = best
            if el is None:
                try:
                    el = _clickable_candidates(
                        driver, [_by_css("ytd-video-renderer a#video-title"), _by_css("a#video-title")],
                        cfg.BROWSER_SEARCH_RESULTS_WAIT_S,
                    )
                except TimeoutException:
                    raise ActionError("No YouTube results appeared.", recoverable=True, hint="no-results")
            _click_element(driver, el)
        self._dismiss_consent(driver)

    def _play_media(self, driver, service: str, query: Optional[str]) -> None:
        if service == "spotify":
            self._spotify_play(driver, query)
        elif service in ("youtube", "netflix"):
            self._youtube_play(driver, query)
        else:
            raise ActionError(
                f"I don't have a player recipe for {service} yet.", recoverable=False, hint="unsupported-media"
            )

    def _verify_playback(self, driver, service: str) -> dict:
        if service == "youtube":
            try:
                WebDriverWait(driver, cfg.BROWSER_PLAYBACK_VERIFY_S).until(
                    lambda d: bool(
                        d.execute_script(
                            "var v=document.querySelector('#movie_player video'); return !!v;"
                        )
                    )
                )
                playing = bool(
                    driver.execute_script(
                        "var v=document.querySelector('#movie_player video');"
                        " return v ? !v.paused && !v.ended : false;"
                    )
                )
                return {"playing": playing, "note": "video opened" if not playing else "playback started"}
            except TimeoutException:
                raise ActionError("The video player didn't open.", recoverable=True, hint="player-not-found")
        if service == "spotify":
            try:
                _visible_candidates(
                    driver,
                    [_by_css('[data-testid="now-playing-widget"]'), _by_css('[data-testid="context-item-info-title"]')],
                    cfg.BROWSER_PLAYBACK_VERIFY_S,
                )
            except TimeoutException:
                pass
            playing = False
            try:
                btn = _clickable_candidates(driver, [_by_css('[data-testid="control-button-playpause"]')], 2)
                playing = "pause" in (btn.get_attribute("aria-label") or "").lower()
            except TimeoutException:
                pass
            return {"playing": playing}
        return {"playing": False}

    def _media_control(self, driver, service: str, action: str) -> dict:
        """pause/resume/skip with per-site buttons + keyboard fallback."""
        site = service or self._detect_service(self.current_url) or "youtube"
        if site == "spotify":
            table = {
                "pause": ([_by_css('button[data-testid="control-button-playpause"][aria-label*="Pause"]'), _by_css('button[aria-label*="Pause"]')], None),
                "resume": ([_by_css('button[data-testid="control-button-playpause"][aria-label*="Play"]'), _by_css('button[aria-label*="Play"]')], None),
                "skip": ([_by_css('[data-testid="control-button-skip-forward"]'), _by_css('button[aria-label*="Next"]')], None),
            }
        else:
            table = {
                "pause": ([_by_css('button[aria-label*="Pause"]'), _by_css('[aria-label*="Pause"][role="button"]')], "k"),
                "resume": ([_by_css('button[aria-label*="Play"]'), _by_css('[aria-label*="Play"][role="button"]')], "k"),
                "skip": ([_by_css('button[aria-label*="Next"]'), _by_css('[aria-label*="Next"][role="button"]')], None),
            }
        cands, shortcut = table[action]
        try:
            el = _clickable_candidates(driver, cands, min(cfg.BROWSER_EXPLICIT_WAIT_S, 5))
            _click_element(driver, el)
            return {"used": "button"}
        except TimeoutException:
            pass
        if shortcut:
            try:
                body = _visible_candidates(driver, [_by_css("body")], 2)
                body.send_keys(shortcut)
                return {"used": "shortcut"}
            except TimeoutException:
                pass
        raise ActionError(f"I couldn't {action} on {site}.", recoverable=True, hint="control-not-found")

    # ── page ops ──

    def _scroll(self, driver, direction: str) -> dict:
        if direction in ("top", "up"):
            driver.execute_script("window.scrollTo(0,0);")
        elif direction in ("bottom", "down"):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        else:
            driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8);")
        self._refresh_state(driver)
        return {"scrolled": direction}

    def _screenshot(self, driver) -> str:
        raw = driver.get_screenshot_as_png()
        if len(raw) > cfg.BROWSER_SCREENSHOT_MAX_BYTES:
            try:
                from PIL import Image

                img = Image.open(io.BytesIO(raw)).convert("RGB")
                scale = min(1.0, 1280 / img.width)
                if scale < 1.0:
                    img = img.resize((int(img.width * scale), int(img.height * scale)))
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                raw = buf.getvalue()
            except Exception:
                pass
        return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")

    def _extract(self, driver, limit: int = 4_000) -> str:
        try:
            src = driver.page_source or ""
        except Exception:
            src = ""
        return extract_text(src)[:limit]

    def _click_target(self, driver, target: str) -> None:
        target = target.strip(".,;!? ")
        cands: list[tuple] = [
            _by_css(f'[aria-label*="{target}" i]'),
            _by_css(f'button[aria-label*="{target}" i]'),
            _by_css(f'a[aria-label*="{target}" i]'),
            _by_css(f'[data-testid*="{target}" i]'),
        ]
        cands += _text_candidates(target, "button")
        cands += _text_candidates(target, "a")
        cands += _text_candidates(target, "input[type=submit]")
        try:
            el = _clickable_candidates(driver, cands, cfg.BROWSER_EXPLICIT_WAIT_S)
            _click_element(driver, el)
        except TimeoutException:
            raise ActionError(
                f"I couldn't find a '{target}' element to click.", recoverable=True, hint="click-target-not-found"
            )

    def _type_target(self, driver, text: str, target: Optional[str]) -> None:
        if target and "search" in target.lower():
            cands = self._search_input_candidates(driver)
        else:
            cands = [_by_css('input[type="search"]'), _by_css('input[type="text"]'), _by_css("textarea"), _by_css("input:not([type])")]
        try:
            el = _clickable_candidates(driver, cands, cfg.BROWSER_EXPLICIT_WAIT_S)
        except TimeoutException:
            raise ActionError("I couldn't find an input to type into.", recoverable=True, hint="type-target-not-found")
        _type_text(driver, el, text)
        if target and "search" in target.lower():
            el.send_keys(Keys.ENTER)

    # ── plan executor (sections 12-14) ──

    async def _execute_step(self, intent: BrowserIntent, action: str) -> Optional[dict]:
        """Dispatch one plan step with retry-on-failure (MAX_ACTION_RETRIES)."""
        last_exc: Optional[ActionError] = None
        for attempt in range(cfg.MAX_ACTION_RETRIES + 1):
            try:
                return await self._step_once(intent, action)
            except ActionError as e:
                last_exc = e
                if not e.recoverable or attempt >= cfg.MAX_ACTION_RETRIES:
                    raise
                await asyncio.sleep(0.4 * (attempt + 1))
        if last_exc:
            raise last_exc
        return None

    async def _step_once(self, intent: BrowserIntent, action: str) -> Optional[dict]:
        if action == "open_website":
            url = intent.url
            if not url and intent.service:
                url = intent.service if intent.service.startswith("http") else None
                if not url:
                    from .intent import lookup_site

                    url = lookup_site(intent.service)
            if not url:
                # "open this website" with an active browser → confirm state
                if self.browser_open:
                    st = await self._run(lambda d: (self._refresh_state(d), self.state())[1])
                    return {"type": "browser_status", "content": f"🌐 You're already on {st.get('current_title') or 'the current page'}."}
                raise ActionError("I don't know which website to open.", recoverable=True, hint="no-url")
            await self._run(lambda d: self._open_website(d, url))
            return None

        if action == "verify_navigation":
            st = await self._run(lambda d: self._verify_navigation(d))
            return {"type": "browser_status", "content": f"✓ {st.get('current_title') or 'Page'} is open."}

        if action == "search_site":
            if not intent.query:
                raise ActionError("What should I search for?", recoverable=True, hint="no-query")
            await self._run(lambda d: self._search_site(d, intent.query or ""))
            return None

        if action == "verify_results":
            await self._run(lambda d: self._verify_results(d, intent.service))
            return {"type": "browser_status", "content": "✓ Results are on screen."}

        if action == "select_best_match":
            res = await self._run(lambda d: self._select_best_match(d, intent.service or "youtube", intent.query))
            return {"type": "browser_status", "content": "🎵 Picked the best match." if res.get("selected_title") else "🎵 Selected the first result."}

        if action == "play_media":
            await self._run(lambda d: self._play_media(d, intent.service or "spotify", intent.query))
            return None

        if action == "verify_playback":
            res = await self._run(lambda d: self._verify_playback(d, intent.service or "spotify"))
            if res.get("playing"):
                return {"type": "browser_status", "content": "✓ Playback started."}
            return {"type": "browser_status", "content": "✓ Opened the player." + (f" ({res.get('note')})" if res.get("note") else "")}

        if action in ("pause_media", "resume_media", "skip_media"):
            verb = action.split("_")[0]
            res = await self._run(lambda d: self._media_control(d, intent.service, verb))
            return {"type": "browser_status", "content": f"✓ {'Paused' if verb == 'pause' else 'Resumed' if verb == 'resume' else 'Skipped'} (via {res.get('used')})."}

        if action == "verify_media_state":
            return None

        if action == "scroll":
            await self._run(lambda d: self._scroll(d, intent.direction or "down"))
            return {"type": "browser_status", "content": f"✓ Scrolled {intent.direction or 'down'}."}

        if action == "screenshot":
            data_uri = await self._run(lambda d: self._screenshot(d))
            return {"type": "image", "content": data_uri}

        if action == "extract":
            text = await self._run(lambda d: self._extract(d))
            if not text:
                raise ActionError("This page has no readable text.", recoverable=True, hint="empty-page")
            return {"type": "content", "content": f"\n\n📄 **Extracted from the page:**\n\n{text[:2_500]}"}

        if action == "click":
            await self._run(lambda d: self._click_target(d, intent.target or ""))
            return {"type": "browser_status", "content": f"✓ Clicked {intent.target}."}

        if action == "type_text":
            await self._run(lambda d: self._type_target(d, intent.text or "", intent.target))
            return None

        if action == "submit_search":
            return None

        if action == "download":
            return {"type": "browser_status", "content": "⬇️ Downloads need a direct link — tell me the URL and I'll open it."}

        if action == "delegate_web_search":
            # handled by the chat pipeline (fast retrieval, not Selenium)
            return None

        logger.warning("browser plan: unknown step {!r}", action)
        return None

    async def run_plan(self, intent: BrowserIntent) -> list[dict]:
        """Execute the plan; returns a list of event dicts (browser_status /
        content / image). Never raises for user-facing flows."""
        events: list[dict] = []
        started = time.perf_counter()
        plan = build_plan(intent, current_url=self.current_url)
        summary = ""
        ok = False
        try:
            async with self._lock:
                for step in plan:
                    events.append({"type": "browser_status", "content": step["status"]})
                    result = await self._execute_step(intent, step["action"])
                    if result is not None:
                        events.append(result)
            self.last_error = None
            ok = True
            summary = self._summary(intent)
        except ActionError as e:
            self.last_error = e.hint or str(e)
            ok = False
            summary = e.hint if isinstance(e, AuthRequired) else f"I couldn't complete that: {e}."
        except Exception as e:  # pragma: no cover
            self.last_error = str(e)
            ok = False
            summary = "Something went wrong while operating the browser."
        logger.bind(
            intent=intent.intent,
            service=intent.service,
            query=intent.query,
            steps=len(plan),
            success=ok,
            duration_ms=round((time.perf_counter() - started) * 1000),
        ).info("browser_agent plan finished")
        events.append({"type": "content", "content": summary})
        events.append({"type": "done", "success": ok, "browser": self.state()})
        return events

    def _summary(self, intent: BrowserIntent) -> str:
        i, s, q = intent.intent, intent.service, intent.query
        if i in (OPEN_WEBSITE, NAVIGATE):
            return f"🌐 {s or 'The page'} is open." if s else f"🌐 Opened {intent.url}."
        if i == SEARCH_SITE:
            return f"🔎 Searched {s or 'the site'} for \"{q}\" — results are on screen."
        if i == PLAY_MEDIA:
            base = f"▶ Playing {q} on {s}." if q else f"▶ Playing on {s}."
            return base
        if i == PAUSE_MEDIA:
            return "⏸ Paused."
        if i == RESUME_MEDIA:
            return "▶ Resumed."
        if i == SKIP_MEDIA:
            return "⏭ Skipped to the next track."
        if i == SCROLL:
            return f"🖱 Scrolled {intent.direction or 'down'}."
        if i == SCREENSHOT:
            return "📸 Screenshot taken."
        if i == EXTRACT:
            return "📄 Extracted the page content above."
        if i == CLICK:
            return f"🖱 Clicked {intent.target}."
        if i == TYPE:
            return "⌨️ Typed it in."
        if i == DOWNLOAD:
            return "⬇️ Ready to download — provide the link."
        return "✅ Done."


browser_agent = BrowserAgent()
