"""Natural language intent detection for OS automation."""

import logging
import re
from typing import Optional, Dict, List, Tuple
from .schema import AutomationIntent, IntentType, RiskLevel

logger = logging.getLogger("hsbot.automation.intent")


class IntentDetector:
    """Detects and classifies user automation intents."""

    APP_ALIASES: Dict[str, List[str]] = {
        "chrome": ["chrome", "google chrome", "browser"],
        "vscode": ["vscode", "vs code", "visual studio code", "code editor", "visual code"],
        "spotify": ["spotify", "music"],
        "discord": ["discord"],
        "teams": ["teams", "microsoft teams"],
        "outlook": ["outlook", "mail", "email"],
        "explorer": ["explorer", "file explorer", "files"],
        "notepad": ["notepad", "notepad++", "text editor"],
        "powershell": ["powershell", "terminal", "cmd", "command prompt"],
        "python": ["python", "python shell"],
        "nodejs": ["node", "nodejs", "npm"],
        "edge": ["edge", "microsoft edge"],
        "firefox": ["firefox", "mozilla firefox"],
        "steam": ["steam"],
        "slack": ["slack"],
        "zoom": ["zoom"],
        "word": ["word", "microsoft word"],
        "excel": ["excel", "microsoft excel"],
        "calculator": ["calculator", "calc"],
        "snipping": ["snipping tool", "snipping"],
    }

    SERVER_HINTS = ("server", "backend", "frontend", "dev server", "development server", "api")

    INTENT_PATTERNS: List[Tuple[str, IntentType, str]] = [
        # ── Window (must precede generic open/close/minimize) ──
        (r"^(?:maximize|fullscreen)\s+(?:this\s+|the\s+)?window$", IntentType.MAXIMIZE_WINDOW, "window"),
        (r"^(?:minimize|hide)\s+(?:this\s+|the\s+)?window$", IntentType.MINIMIZE_WINDOW, "window"),
        (r"^(?:restore|restore this)\s+(?:the\s+)?window$", IntentType.RESTORE_WINDOW, "window"),
        (r"^(?:close|close this)\s+(?:this\s+|the\s+)?window$", IntentType.CLOSE_WINDOW, "window"),
        (r"^(?:snap|dock)\s+(?:this\s+|the\s+)?window\s+to\s+(?:the\s+)?left$", IntentType.SNAP_WINDOW_LEFT, "window"),
        (r"^(?:snap|dock)\s+(?:this\s+|the\s+)?window\s+to\s+(?:the\s+)?right$", IntentType.SNAP_WINDOW_RIGHT, "window"),
        (r"^(?:move|put)\s+(?:chrome|edge|firefox|browser)?\s*to\s+(?:the\s+)?left\s+side$", IntentType.SNAP_WINDOW_LEFT, "window"),
        (r"^(?:move|put)\s+(?:chrome|edge|firefox|browser)?\s*to\s+(?:the\s+)?right\s+side$", IntentType.SNAP_WINDOW_RIGHT, "window"),
        (r"^(?:show|display)\s+(?:the\s+)?desktop$", IntentType.SHOW_DESKTOP, "window"),
        (r"^(?:maximize|minimize|restore)\s+this$", IntentType.MAXIMIZE_WINDOW, "window"),

        # ── Application ──
        (r"^(?:open|launch|start)\s+(?:up\s+)?(?!(?:the\s+)?(?:folder|file|document|directory)\b)(.+?)$", IntentType.OPEN_APPLICATION, "application"),
        (r"^(?:close|quit|exit|kill)\s+(.+?)$", IntentType.CLOSE_APPLICATION, "application"),
        (r"^(?:switch to|go to|jump to|switch)\s+(.+?)$", IntentType.SWITCH_APPLICATION, "application"),
        (r"^(?:minimize|hide)\s+(.+?)$", IntentType.MINIMIZE_APPLICATION, "application"),
        (r"^(?:maximize|fullscreen)\s+(.+?)$", IntentType.MAXIMIZE_APPLICATION, "application"),
        (r"^(?:restart|relaunch)\s+(?!(?:the\s+)?(?:computer|pc|laptop)(?:\s|$))(.+?)$", IntentType.RESTART_APPLICATION, "application"),

        # ── File ──
        (r"^(?:create|make)\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+|named\s+)?(.+?)$", IntentType.CREATE_FILE, "file"),
        (r"^(?:create|make)\s+(?:a\s+)?(?:new\s+)?(?:text\s+|txt\s+)?(?:document|notes)\s+(?:called\s+|named\s+)?(.+?)$", IntentType.CREATE_FILE, "file"),
        (r"^(?:delete|remove|erase)\s+(?:the\s+)?file\s+(.+?)$", IntentType.DELETE_FILE, "file"),
        (r"^(?:delete|remove|erase)\s+file\s*$", IntentType.DELETE_FILE, "file"),
        (r"^(?:rename)\s+(?:the\s+)?file\s+(.+?)\s+(?:to|as)\s+(.+?)$", IntentType.RENAME_FILE, "file"),
        (r"^(?:copy)\s+(?:the\s+)?file\s+(.+?)\s+(?:to|into)\s+(.+?)$", IntentType.COPY_FILE, "file"),
        (r"^(?:move)\s+(?:the\s+)?file\s+(.+?)\s+(?:to|into)\s+(.+?)$", IntentType.MOVE_FILE, "file"),
        (r"^(?:find|search|look for)\s+all\s+(.+?)\s+files?\s+in\s+(.+?)$", IntentType.SEARCH_FILES, "file"),
        (r"^(?:find|search|look for)\s+(?:the\s+)?(?:files?|documents?)\s+(?:matching\s+|named\s+|called\s+|with\s+)?(.+?)$", IntentType.SEARCH_FILES, "file"),
        (r"^(?:find|search|look for)\s+(?:all\s+)?(.+?)\s+(?:files?|documents?)$", IntentType.SEARCH_FILES, "file"),
        (r"^(?:show|get|read)\s+(?:the\s+)?(?:info|metadata|details)\s+(?:for|of)\s+(?:the\s+)?file\s+(.+?)$", IntentType.FILE_METADATA, "file"),
        (r"^(?:open)\s+(?:the\s+)?file\s+(.+?)$", IntentType.OPEN_FILE, "file"),
        (r"^(?:open|view|show)\s+(.+?\.(?:txt|md|pdf|docx?|xlsx?|pptx|csv|json|py|ts|js|html))$", IntentType.OPEN_FILE, "file"),
        (r"^(?:rename)\s+(.+?)\s+(?:to|as)\s+(.+?)$", IntentType.RENAME_FILE, "file"),

        # ── Folder ──
        (r"^(?:create|make)\s+(?:a\s+)?(?:new\s+)?folder\s+(?:called\s+|named\s+)?(.+?)$", IntentType.CREATE_FOLDER, "folder"),
        (r"^(?:create|make)\s+(?:a\s+)?(?:new\s+)?(?:project|directory)\s+(?:called\s+|named\s+)?(.+?)$", IntentType.CREATE_FOLDER, "folder"),
        (r"^(?:delete|remove|erase)\s+(?:the\s+)?folder\s+(.+?)$", IntentType.DELETE_FOLDER, "folder"),
        (r"^(?:rename)\s+(?:the\s+)?folder\s+(.+?)\s+(?:to|as)\s+(.+?)$", IntentType.RENAME_FOLDER, "folder"),
        (r"^(?:copy)\s+(?:the\s+)?folder\s+(.+?)\s+(?:to|into)\s+(.+?)$", IntentType.COPY_FOLDER, "folder"),
        (r"^(?:move)\s+(?:the\s+)?folder\s+(.+?)\s+(?:to|into)\s+(.+?)$", IntentType.MOVE_FOLDER, "folder"),
        (r"^(?:find|search)\s+(?:for\s+)?(?:the\s+)?(?:folder|directories?)\s+(?:called\s+|named\s+)?(.+?)$", IntentType.SEARCH_FOLDERS, "folder"),
        (r"^(?:open)\s+(?:the\s+)?folder\s+(.+?)$", IntentType.OPEN_FOLDER, "folder"),
        (r"^(?:open|show)\s+(?:my\s+)?(?:downloads?|documents?|desktop|pictures?|music|videos?|projects?)\s*(?:folder)?$", IntentType.OPEN_FOLDER, "folder"),
        (r"^(?:open)\s+(.+?)$", IntentType.OPEN_FOLDER, "folder"),

        # ── Keyboard ──
        (r"^(?:press|hit|tap)\s+(.+?)$", IntentType.KEY_PRESS, "keyboard"),
        (r"^(?:type|enter|input)\s+(.+?)$", IntentType.TYPE_TEXT, "keyboard"),

        # ── Mouse ──
        (r"^(?:left-?)?click$", IntentType.CLICK, "mouse"),
        (r"^(?:click)\s+(?:the\s+)?(?:start|button|menu)\s+button$", IntentType.CLICK, "mouse"),
        (r"^(?:double[- ]click|double click)\s*$", IntentType.DOUBLE_CLICK, "mouse"),
        (r"^(?:right[- ]click|right click)\s*$", IntentType.RIGHT_CLICK, "mouse"),
        (r"^(?:scroll|roll)\s+(down|up)\s*$", IntentType.SCROLL, "mouse"),
        (r"^(?:scroll|roll)\s*(?:down|up)?\s*$", IntentType.SCROLL, "mouse"),
        (r"^(?:move)\s+(?:the\s+)?(?:cursor|mouse)\s+(?:to\s+)?(.+?)$", IntentType.DRAG, "mouse"),

        # ── Generic file move/copy (after specific folder/snap patterns) ──
        (r"^(?:move|transfer)\s+(.+?)\s+(?:to|into)\s+(.+?)$", IntentType.MOVE_FILE, "file"),
        (r"^(?:copy)\s+(.+?)\s+(?:to|into)\s+(.+?)$", IntentType.COPY_FILE, "file"),

        # ── System ──
        (r"^(?:check|get|show|what is|what's)\s+.*?(?:cpu|processor)\s+(?:and|&)\s+.*?(?:ram|memory)\s+usage$", IntentType.GET_CPU_USAGE, "system"),
        (r"^(?:set|change|turn)\s+(?:the\s+)?volume\s+to\s+(\d+)\s*%?$", IntentType.SET_VOLUME, "system"),
        (r"^(?:volume)\s+to\s+(\d+)\s*%?$", IntentType.SET_VOLUME, "system"),
        (r"^(?:increase|turn up|raise|make louder|max volume)\s+(?:the\s+)?volume(?:\s+by\s+(\d+)\s*%?)?$", IntentType.ADJUST_VOLUME, "system"),
        (r"^(?:decrease|turn down|lower|reduce|make quieter)\s+(?:the\s+)?volume(?:\s+by\s+(\d+)\s*%?)?$", IntentType.ADJUST_VOLUME, "system"),
        (r"^(?:what is|what'?s|check|show|get)\s+(?:the\s+)?(?:current\s+)?volume$", IntentType.GET_VOLUME, "system"),
        (r"^(?:set|change|adjust)\s+(?:the\s+)?brightness\s+to\s+(\d+)\s*%?$", IntentType.SET_BRIGHTNESS, "system"),
        (r"^(?:check|get|show)\s+(?:the\s+)?brightness$", IntentType.GET_BRIGHTNESS, "system"),
        (r"^(?:check|get|show)\s+(?:my\s+)?(?:cpu|processor)\s+usage$", IntentType.GET_CPU_USAGE, "system"),
        (r"^(?:check|get|show)\s+(?:my\s+)?(?:ram|memory)\s+usage$", IntentType.GET_RAM_USAGE, "system"),
        (r"^(?:check|get|show)\s+(?:my\s+)?(?:disk|storage)\s+usage$", IntentType.GET_DISK_USAGE, "system"),
        (r"^(?:take|capture|grab)\s+(?:a\s+)?screenshot$", IntentType.TAKE_SCREENSHOT, "system"),
        (r"^(?:lock|lock up)\s+(?:my\s+|the\s+|this\s+)?(?:screen|computer|pc|laptop)$", IntentType.LOCK_SCREEN, "system"),
        (r"^(?:sleep|go to sleep|put (?:the|my)? ?computer to sleep)$", IntentType.SLEEP, "system"),
        (r"^(?:restart|reboot)\s+(?:the\s+)?(?:computer|pc|laptop)?$", IntentType.RESTART, "system"),
        (r"^(?:shutdown|shut down|turn off|power off)\s+(?:the\s+)?(?:computer|pc|laptop)?$", IntentType.SHUTDOWN, "system"),
        (r"^(?:check|show|get)\s+(?:wifi|wi-?fi)\s+status$", IntentType.CHECK_WIFI, "system"),
        (r"^(?:check|show|get)\s+(?:bluetooth)\s+status$", IntentType.CHECK_BLUETOOTH, "system"),
        (r"^(?:check|show|get)\s+(?:network|internet|connection)\s+status$", IntentType.CHECK_NETWORK, "system"),
        (r"^(?:check|show|get)\s+(?:battery)\s+status$", IntentType.CHECK_BATTERY, "system"),

        # ── Browser ──
        (r"^(?:open|visit|go to|navigate to)\s+(.+?)$", IntentType.OPEN_URL, "browser"),
        (r"^(?:search|google|bing)\s+(?:google\s+|bing\s+)?(?:the\s+web\s+)?(?:for\s+)?(.+?)$", IntentType.SEARCH_WEB, "browser"),
        (r"^(?:open|new)\s+(?:a\s+)?(?:new\s+)?tab$", IntentType.OPEN_NEW_TAB, "browser"),
        (r"^(?:close)\s+(?:this\s+|the\s+)?(?:tab|current tab)$", IntentType.CLOSE_TAB, "browser"),
        (r"^(?:refresh|reload)\s+(?:the\s+)?(?:page|tab|browser)?$", IntentType.REFRESH_PAGE, "browser"),
        (r"^(?:go\s+)?back$", IntentType.GO_BACK, "browser"),
        (r"^(?:go\s+)?forward$", IntentType.GO_FORWARD, "browser"),

        # ── Process / Terminal ──
        (r"^(?:show|list)\s+(?:running\s+|all\s+|top\s+)?processes$", IntentType.LIST_PROCESSES, "process"),
        (r"^(?:stop|kill|end|terminate)\s+(?:the\s+)?(.+?)$", IntentType.STOP_PROCESS, "process"),
        (r"^(?:restart)\s+(?:the\s+)?(.+?)(?:\s+(?:server|process|service))?$", IntentType.RESTART_PROCESS, "process"),
        (r"^(?:start)\s+(?:the\s+)?(.+?)(?:\s+(?:server|service))?$", IntentType.START_PROCESS, "process"),
        (r"^(?:monitor|track)\s+(.+?)$", IntentType.MONITOR_PROCESS, "process"),
        (r"^(?:run|execute)\s+(?:the\s+)?script\s+(.+?)$", IntentType.RUN_SCRIPT, "terminal"),
        (r"^(?:run|execute)\s+(.+?)$", IntentType.RUN_COMMAND, "terminal"),
    ]

    _CLEANUP_PATTERNS = [
        re.compile(r"^\s*(?:wake\s*up|wakeup)[,\s.!]*\s*", re.I),
        re.compile(r"^\s*(?:hey\s+)?(?:hs(?:bot)?|assistant|hs\s+b?o?t?)[,\s.!]*\s*", re.I),
        re.compile(r"^\s*(?:can|could|would|will|do)\s+you\s+(?:please\s+)?", re.I),
        re.compile(r"^\s*(?:please|kindly)\s+", re.I),
        re.compile(r"\s+please\s*$", re.I),
        re.compile(r"\s*\?+\s*$", re.I),
        re.compile(r"^\s*(?:go ahead and|let'?s|lets)\s+", re.I),
    ]

    _SITES = {
        "youtube", "github", "gmail", "google", "spotify", "facebook", "twitter",
        "instagram", "linkedin", "reddit", "netflix", "amazon", "wikipedia",
        "stackoverflow", "whatsapp", "telegram", "discord web", "maps", "news",
        "chatgpt", "claude", "gemini", "x", "twitch", "pinterest", "tiktok",
        "zomato", "swiggy", "flipkart", "ebay", "codepen", "replit", "vercel",
        "huggingface", "kaggle", "medium", "dev.to", "notion", "trello", "slack web",
    }

    def _clean(self, command: str) -> str:
        text = command.strip()
        for pattern in self._CLEANUP_PATTERNS:
            text = pattern.sub("", text)
        return text.strip().lower()

    _KNOWN_FOLDERS = {
        "downloads": "downloads", "download folder": "downloads", "my downloads": "downloads",
        "documents": "documents", "document folder": "documents", "my documents": "documents",
        "desktop": "desktop", "my desktop": "desktop",
        "pictures": "pictures", "photos": "pictures", "music": "music", "videos": "videos",
        "projects": "projects", "home": "home", "home folder": "home",
    }

    def _detect_url_intent(self, command_lower: str) -> Optional[AutomationIntent]:
        """Pre-pass: 'open/visit/go to X' where X is a website → browser OPEN_URL."""
        m = re.match(r"^(?:open|visit|go to|navigate to)\s+(?:the\s+)?(.+?)$", command_lower)
        if not m:
            return None
        target = m.group(1).strip().strip('"').lower()
        if not target:
            return None
        # Known user folders beat app launch ("open my downloads").
        if target in self._KNOWN_FOLDERS:
            return AutomationIntent(
                intent=IntentType.OPEN_FOLDER,
                category="folder",
                target=self._KNOWN_FOLDERS[target],
                parameters={"path": self._KNOWN_FOLDERS[target]},
                confidence=0.95,
                risk_level=RiskLevel.LOW,
                requires_confirmation=False,
                explanation=f"Open folder: {target}",
            )
        is_site = target in self._SITES
        is_url = ("." in target and " " not in target and not re.search(r"\.(txt|md|pdf|docx?|xlsx?|pptx|csv|json|py|ts|js|html|png|jpg|jpeg|gif)$", target)) \
            or target.startswith("localhost") or "://" in target or ":" in target.split("/")[0]
        if is_site or is_url:
            return AutomationIntent(
                intent=IntentType.OPEN_URL,
                category="browser",
                target=target,
                parameters={"url": target},
                confidence=0.92,
                risk_level=RiskLevel.LOW,
                requires_confirmation=False,
                explanation=f"Open URL: {target}",
            )
        return None

    def detect_intent(self, user_command: str) -> AutomationIntent:
        """Detect and classify a user's automation intent."""
        command_lower = self._clean(user_command)
        if not command_lower:
            return self._unknown(user_command)

        url_intent = self._detect_url_intent(command_lower)
        if url_intent:
            return url_intent

        # Combined system check: "check cpu and ram usage" → one intent, both metrics.
        combined = re.match(
            r"^(?:check|get|show|what is|what's)\s+.*?(?:cpu|processor)(?:\s+usage)?\s+(?:and|&)\s+.*?(?:ram|memory)(?:\s+usage)?$",
            command_lower,
        )
        if combined:
            return AutomationIntent(
                intent=IntentType.GET_CPU_USAGE,
                category="system",
                target=None,
                parameters={"combined": ["cpu", "ram"]},
                confidence=0.95,
                risk_level=RiskLevel.LOW,
                requires_confirmation=False,
                explanation="Check CPU and RAM usage",
            )

        for pattern, intent_type, category in self.INTENT_PATTERNS:
            match = re.search(pattern, command_lower, re.IGNORECASE)
            if not match:
                continue
            groups = match.groups()
            target = None
            params: Dict = {}

            if intent_type in (IntentType.OPEN_APPLICATION, IntentType.CLOSE_APPLICATION,
                               IntentType.SWITCH_APPLICATION, IntentType.MINIMIZE_APPLICATION,
                               IntentType.MAXIMIZE_APPLICATION, IntentType.RESTART_APPLICATION,
                               IntentType.OPEN_URL, IntentType.SEARCH_WEB, IntentType.KEY_PRESS,
                               IntentType.TYPE_TEXT, IntentType.STOP_PROCESS, IntentType.START_PROCESS,
                               IntentType.RESTART_PROCESS, IntentType.MONITOR_PROCESS,
                               IntentType.RUN_COMMAND, IntentType.RUN_SCRIPT, IntentType.OPEN_FOLDER,
                               IntentType.OPEN_FILE, IntentType.SEARCH_FILES, IntentType.SEARCH_FOLDERS):
                target = groups[0].strip().strip('"') if groups and groups[0] else None
                # Normalize: "open the calculator" → target "calculator"
                if target and intent_type in (IntentType.OPEN_APPLICATION, IntentType.CLOSE_APPLICATION,
                                              IntentType.SWITCH_APPLICATION, IntentType.MINIMIZE_APPLICATION,
                                              IntentType.MAXIMIZE_APPLICATION, IntentType.RESTART_APPLICATION,
                                              IntentType.STOP_PROCESS, IntentType.START_PROCESS,
                                              IntentType.RESTART_PROCESS, IntentType.MONITOR_PROCESS,
                                              IntentType.RUN_COMMAND, IntentType.RUN_SCRIPT):
                    target = re.sub(r"^(?:the|a|an)\s+", "", target, count=1).strip()
                    if not target:
                        target = None
            elif intent_type in (IntentType.CREATE_FILE, IntentType.CREATE_FOLDER):
                target = groups[0].strip().strip('"') if groups and groups[0] else None
                if target:
                    params["name"] = target
            elif intent_type in (IntentType.DELETE_FILE, IntentType.DELETE_FOLDER):
                target = groups[0].strip().strip('"') if groups and groups[0] else None
            elif intent_type in (IntentType.RENAME_FILE, IntentType.RENAME_FOLDER,
                                 IntentType.COPY_FILE, IntentType.MOVE_FILE,
                                 IntentType.COPY_FOLDER, IntentType.MOVE_FOLDER):
                target = groups[0].strip().strip('"') if groups and groups[0] else None
                if len(groups) > 1 and groups[1]:
                    params["destination"] = groups[1].strip().strip('"')
                    params["new_name"] = groups[1].strip().strip('"')
            elif intent_type in (IntentType.SET_VOLUME, IntentType.SET_BRIGHTNESS):
                params["level"] = int(groups[0]) if groups and groups[0] else 50
            elif intent_type == IntentType.ADJUST_VOLUME:
                params["direction"] = "up" if any(w in command_lower for w in ("up", "increase", "raise", "louder", "max")) else "down"
                if groups and groups[0]:
                    params["delta"] = int(groups[0])
            elif intent_type == IntentType.SCROLL:
                params["direction"] = groups[0] if groups and groups[0] else "down"

            if intent_type in (IntentType.OPEN_APPLICATION, IntentType.CLOSE_APPLICATION,
                               IntentType.SWITCH_APPLICATION, IntentType.MINIMIZE_APPLICATION,
                               IntentType.MAXIMIZE_APPLICATION, IntentType.RESTART_APPLICATION) and target:
                params["app"] = self._normalize_app_name(target)

            # "start the backend/frontend" is a process/server start, not an app
            if intent_type in (IntentType.OPEN_APPLICATION, IntentType.START_PROCESS,
                               IntentType.RESTART_APPLICATION, IntentType.CLOSE_APPLICATION) and target:
                if any(hint in target.lower() for hint in self.SERVER_HINTS):
                    if intent_type == IntentType.RESTART_APPLICATION:
                        intent_type = IntentType.RESTART_PROCESS
                    elif intent_type == IntentType.CLOSE_APPLICATION:
                        intent_type = IntentType.STOP_PROCESS
                    else:
                        intent_type = IntentType.START_PROCESS
                    params["server"] = target.lower()

            risk_level = self._classify_risk(intent_type)
            requires_confirmation = risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)

            return AutomationIntent(
                intent=intent_type,
                category=category,
                target=target,
                parameters=params,
                confidence=0.9,
                risk_level=risk_level,
                requires_confirmation=requires_confirmation,
                explanation=self._generate_explanation(intent_type, target, params),
            )

        return self._unknown(user_command)

    def _unknown(self, command: str) -> AutomationIntent:
        return AutomationIntent(
            intent=IntentType.UNKNOWN,
            category="unknown",
            target=command,
            parameters={},
            confidence=0.0,
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            explanation=f"Could not understand the automation command: '{command}'",
        )

    def _normalize_app_name(self, app_name: str) -> str:
        """Normalize application names using aliases."""
        app_lower = app_name.lower().strip()
        if any(hint in app_lower for hint in self.SERVER_HINTS):
            return app_lower
        for canonical, aliases in self.APP_ALIASES.items():
            if app_lower in aliases or app_lower == canonical:
                return canonical
            for alias in aliases:
                if app_lower.startswith(alias + " ") or app_lower.endswith(" " + alias):
                    return canonical
        return app_lower

    def _classify_risk(self, intent: IntentType) -> RiskLevel:
        """Classify the risk level of an intent (spec §4)."""
        critical_intents = {
            IntentType.SHUTDOWN,
            IntentType.RESTART,
            IntentType.DELETE_FILE,
            IntentType.DELETE_FOLDER,
            IntentType.RUN_SCRIPT,
        }
        high_intents = {
            IntentType.RUN_COMMAND,
        }
        medium_intents = {
            IntentType.MOVE_FILE,
            IntentType.MOVE_FOLDER,
            IntentType.RENAME_FILE,
            IntentType.RENAME_FOLDER,
            IntentType.STOP_PROCESS,
            IntentType.RESTART_PROCESS,
            IntentType.CLOSE_APPLICATION,
            IntentType.SLEEP,
        }
        if intent in critical_intents:
            return RiskLevel.CRITICAL
        if intent in high_intents:
            return RiskLevel.HIGH
        if intent in medium_intents:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _generate_explanation(self, intent: IntentType, target: Optional[str], params: dict) -> str:
        """Generate human-readable explanation of the action."""
        explanations = {
            IntentType.OPEN_APPLICATION: f"Open {target or 'application'}",
            IntentType.CLOSE_APPLICATION: f"Close {target or 'application'}",
            IntentType.SWITCH_APPLICATION: f"Switch to {target or 'application'}",
            IntentType.MINIMIZE_APPLICATION: f"Minimize {target or 'application'}",
            IntentType.MAXIMIZE_APPLICATION: f"Maximize {target or 'application'}",
            IntentType.RESTART_APPLICATION: f"Restart {target or 'application'}",
            IntentType.CREATE_FOLDER: f"Create folder: {target or 'New Folder'}",
            IntentType.CREATE_FILE: f"Create file: {target or 'New File'}",
            IntentType.DELETE_FILE: f"Delete file: {target or 'file'}",
            IntentType.DELETE_FOLDER: f"Delete folder: {target or 'folder'}",
            IntentType.RENAME_FILE: f"Rename {target} to {params.get('new_name', '?')}",
            IntentType.RENAME_FOLDER: f"Rename folder {target} to {params.get('new_name', '?')}",
            IntentType.MOVE_FILE: f"Move {target} to {params.get('destination', '?')}",
            IntentType.MOVE_FOLDER: f"Move folder {target} to {params.get('destination', '?')}",
            IntentType.COPY_FILE: f"Copy {target} to {params.get('destination', '?')}",
            IntentType.COPY_FOLDER: f"Copy folder {target} to {params.get('destination', '?')}",
            IntentType.SEARCH_FILES: f"Search files matching '{target}'",
            IntentType.SEARCH_FOLDERS: f"Search folders matching '{target}'",
            IntentType.FILE_METADATA: f"Read metadata for {target}",
            IntentType.OPEN_FOLDER: f"Open folder: {target or 'location'}",
            IntentType.OPEN_FILE: f"Open file: {target}",
            IntentType.KEY_PRESS: f"Press {target}",
            IntentType.TYPE_TEXT: f"Type '{target}'",
            IntentType.CLICK: "Click",
            IntentType.RIGHT_CLICK: "Right click",
            IntentType.DOUBLE_CLICK: "Double click",
            IntentType.SCROLL: f"Scroll {params.get('direction', '')}",
            IntentType.DRAG: f"Move cursor: {target}",
            IntentType.SET_VOLUME: f"Set volume to {params.get('level', '?')}%",
            IntentType.ADJUST_VOLUME: f"{params.get('direction', 'adjust').title()} volume",
            IntentType.GET_VOLUME: "Read current volume",
            IntentType.GET_CPU_USAGE: "Check CPU usage",
            IntentType.GET_RAM_USAGE: "Check RAM usage",
            IntentType.GET_DISK_USAGE: "Check disk usage",
            IntentType.TAKE_SCREENSHOT: "Take a screenshot",
            IntentType.LOCK_SCREEN: "Lock the screen",
            IntentType.SLEEP: "Put computer to sleep",
            IntentType.RESTART: "Restart the computer",
            IntentType.SHUTDOWN: "Shut down the computer",
            IntentType.CHECK_WIFI: "Check Wi-Fi status",
            IntentType.CHECK_BLUETOOTH: "Check Bluetooth status",
            IntentType.CHECK_NETWORK: "Check network status",
            IntentType.CHECK_BATTERY: "Check battery status",
            IntentType.GET_BRIGHTNESS: "Check brightness",
            IntentType.SET_BRIGHTNESS: f"Set brightness to {params.get('level', '?')}%",
            IntentType.MAXIMIZE_WINDOW: "Maximize window",
            IntentType.MINIMIZE_WINDOW: "Minimize window",
            IntentType.RESTORE_WINDOW: "Restore window",
            IntentType.CLOSE_WINDOW: "Close window",
            IntentType.SNAP_WINDOW_LEFT: "Snap window left",
            IntentType.SNAP_WINDOW_RIGHT: "Snap window right",
            IntentType.SHOW_DESKTOP: "Show desktop",
            IntentType.OPEN_URL: f"Open URL: {target or 'link'}",
            IntentType.SEARCH_WEB: f"Search the web for: {target or 'query'}",
            IntentType.OPEN_NEW_TAB: "Open a new tab",
            IntentType.CLOSE_TAB: "Close tab",
            IntentType.REFRESH_PAGE: "Refresh page",
            IntentType.GO_BACK: "Go back",
            IntentType.GO_FORWARD: "Go forward",
            IntentType.LIST_PROCESSES: "List running processes",
            IntentType.START_PROCESS: f"Start {target or 'process'}",
            IntentType.STOP_PROCESS: f"Stop {target or 'process'}",
            IntentType.RESTART_PROCESS: f"Restart {target or 'process'}",
            IntentType.MONITOR_PROCESS: f"Monitor {target or 'process'}",
            IntentType.RUN_COMMAND: f"Run command: {target or 'command'}",
            IntentType.RUN_SCRIPT: f"Run script: {target}",
            IntentType.UNKNOWN: f"Unknown command: {target}",
        }
        return explanations.get(intent, f"Execute: {intent.value}")


intent_detector = IntentDetector()
