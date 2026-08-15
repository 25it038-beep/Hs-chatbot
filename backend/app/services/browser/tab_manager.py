"""TabManager — multi-tab control for the interactive Chrome session (§5-7).

Tracks every tab Selenium has open (via `driver.window_handles`), resolves
tabs by service name ("switch to Spotify"), opens/creates tabs, closes tabs
and supports "previous tab" navigation. All methods are sync and safe to run
in the agent's worker thread (`agent._run`); they never raise for
user-facing flows — failures surface as empty results / ActionErrors from
the caller.

The controlled Chrome is a SEPARATE window from the HS AI desktop overlay,
so opening tabs here never touches the HS AI chat UI (§1/§20).
"""

from collections import deque
from typing import Callable, Optional
import time

# Hard cap: never enumerate more than this many tabs per state snapshot.
MAX_TRACKED_TABS = 12


class TabManager:
    def __init__(self, detect_service_fn: Callable[[Optional[str]], Optional[str]]) -> None:
        self._driver = None
        self._detect = detect_service_fn
        self._history: deque[str] = deque(maxlen=8)
        self._cache: Optional[list[dict]] = None
        self._cache_time: float = 0.0
        self._cache_ttl: float = 0.3  # Cache tab list for 300ms to prevent flicker

    # ── lifecycle ──

    def attach(self, driver) -> None:
        self._driver = driver
        self._history.clear()
        self._cache = None
        self._cache_time = 0.0

    def detach(self) -> None:
        self._driver = None
        self._history.clear()
        self._cache = None
        self._cache_time = 0.0

    def _ensure(self):
        if self._driver is None:
            raise RuntimeError("no driver attached")
        return self._driver

    # ── snapshot ──

    def tabs(self, driver=None) -> list[dict]:
        """[{id, title, url, active, service}] — never raises, caps at
        MAX_TRACKED_TABS. Titles require switching windows, so the active
        tab is restored afterwards. Results are cached for 300ms to prevent
        rapid tab-switching flicker when multiple lookups happen in sequence."""
        driver = driver or self._driver
        if driver is None:
            return []
        
        # Check cache validity
        now = time.time()
        if self._cache is not None and (now - self._cache_time) < self._cache_ttl:
            return self._cache
        
        try:
            handles = driver.window_handles[:MAX_TRACKED_TABS]
            active = driver.current_window_handle
        except Exception:
            return []
        out: list[dict] = []
        try:
            for h in handles:
                try:
                    driver.switch_to.window(h)
                    url = (driver.current_url or "").strip()
                    title = (driver.title or "").strip()
                except Exception:
                    url = title = ""
                out.append(
                    {
                        "id": h,
                        "title": title or url or "New tab",
                        "url": url,
                        "active": h == active,
                        "service": self._detect(url),
                    }
                )
            try:
                driver.switch_to.window(active)
            except Exception:
                pass
        except Exception:
            return out
        
        # Cache the result
        self._cache = out
        self._cache_time = now
        return out

    # ── lookups ──

    def find(self, driver, service: str) -> Optional[dict]:
        """First open tab whose detected service matches (exact)."""
        if not service or service in ("current", "previous"):
            return None
        for t in self.tabs(driver):
            if t["service"] == service:
                return t
        return None

    def find_by_url(self, driver, url: str) -> Optional[dict]:
        for t in self.tabs(driver):
            if url and url in (t.get("url") or ""):
                return t
        return None

    def active(self, driver) -> Optional[dict]:
        for t in self.tabs(driver):
            if t["active"]:
                return t
        return None

    def is_active(self, driver, tab_id: str) -> bool:
        try:
            return driver.current_window_handle == tab_id
        except Exception:
            return False

    # ── operations ──

    def _remember(self, driver) -> None:
        try:
            self._history.append(driver.current_window_handle)
        except Exception:
            pass

    def switch_to_handle(self, driver, tab_id: str) -> dict:
        """Switch the Selenium context to an existing tab handle."""
        if self.is_active(driver, tab_id):
            return self.active(driver) or {"id": tab_id}
        self._remember(driver)
        driver.switch_to.window(tab_id)
        self._cache = None  # Invalidate cache after switch
        for t in self.tabs(driver):
            if t["id"] == tab_id:
                return t
        return {"id": tab_id}

    def switch_to_service(self, driver, service: str) -> Optional[dict]:
        """Switch to the open tab for a service; None if no such tab."""
        tab = self.find(driver, service)
        if tab is None:
            return None
        return self.switch_to_handle(driver, tab["id"])

    def switch_previous(self, driver) -> Optional[dict]:
        """Back to the previously active tab (browser-history style)."""
        handles = driver.window_handles
        if len(handles) < 2:
            return None
        cur = driver.current_window_handle
        idx = handles.index(cur) if cur in handles else 0
        target = handles[idx - 1]
        self._remember(driver)
        driver.switch_to.window(target)
        self._cache = None  # Invalidate cache after switch
        return self.active(driver)

    def open_tab(self, driver, url: str) -> dict:
        """Create a NEW tab, navigate it and leave it active."""
        self._remember(driver)
        driver.switch_to.new_window("tab")
        driver.get(url)
        self._cache = None  # Invalidate cache after opening
        return self.active(driver) or {"url": url}

    def close_tab(self, driver, tab_id: str) -> Optional[dict]:
        """Close a tab and land on a remaining one. Refuses to close the
        last remaining tab (the agent would have nothing to show)."""
        handles = driver.window_handles
        if len(handles) <= 1:
            raise RuntimeError("last-tab")
        was_active = driver.current_window_handle == tab_id
        try:
            driver.switch_to.window(tab_id)
            title = driver.title or ""
        except Exception:
            return None
        try:
            driver.close()
        except Exception:
            return None
        remaining = [h for h in (driver.window_handles or []) if h != tab_id]
        if not remaining:
            raise RuntimeError("last-tab")
        try:
            driver.switch_to.window(remaining[-1])
        except Exception:
            pass
        self._cache = None  # Invalidate cache after closing
        return {"id": tab_id, "title": title, "url": driver.current_url or ""}
