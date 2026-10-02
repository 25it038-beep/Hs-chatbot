"""
Live Voice Tool Orchestrator & Fast Data Layer for HSBot.
Enables real-time data retrieval (Time, Weather, Web Search, Location, RAG)
for conversational voice turns without adding extra LLM calls or latency to normal chatter.
"""

import asyncio
import logging
import re
import time
from typing import Dict, Any, Optional, Tuple, List

from app.services.tools.time_tool import get_current_time as get_time_data
from app.services.tools.weather_tool import WeatherService
from app.services.tools.location_service import resolve_city_to_location, ip_fallback_location
from app.services.tools.detector import detect_intent as detect_time_weather
from app.services.websearch import WebSearchService
from app.web.search_router import determine_search_mode
from app.web.models import SearchMode
from app.services.rag import RAGService

logger = logging.getLogger("hsbot.live.tools")

# In-memory short-TTL cache for Live Voice queries
# Key: cache_key -> (timestamp, formatted_result_text)
_LIVE_CACHE: Dict[str, Tuple[float, str]] = {}
CACHE_TTL_WEATHER_S = 600.0   # 10 minutes for weather
CACHE_TTL_SEARCH_S = 300.0    # 5 minutes for news/web search
CACHE_TTL_LOCATION_S = 3600.0 # 1 hour for location

_STOP_WORDS = {
    "is", "it", "now", "today", "tomorrow", "tonight", "yesterday",
    "please", "the", "a", "an", "here", "outside", "there", "my",
    "location", "me", "this", "current", "right", "tell", "what",
    "whats", "like", "how", "in", "at", "for"
}

# Explicit location queries
_LOCATION_PATTERNS = [
    re.compile(r"\bwhere am i\b", re.I),
    re.compile(r"\bwhat(?:['’]s| is) my location\b", re.I),
    re.compile(r"\bmy current location\b", re.I),
    re.compile(r"\bwhere is my location\b", re.I),
    re.compile(r"\bwhat location am i in\b", re.I),
    re.compile(r"\bwhat city am i in\b", re.I),
]

# Explicit RAG / uploaded documents query patterns
_RAG_PATTERNS = [
    re.compile(r"\b(my|the|uploaded)\s+(files?|documents?|notes?|pdfs?|papers?|data)\b", re.I),
    re.compile(r"\bin (my|the) (file|document|pdf|upload)\b", re.I),
    re.compile(r"\bfrom (my|the) (file|document|pdf|upload)\b", re.I),
    re.compile(r"\bwhat does (my|the) (file|document|pdf) say\b", re.I),
]

# Conversational chatter patterns that must NEVER trigger external tools
_SMALLTALK_PATTERNS = [
    re.compile(r"^\s*(hi|hello|hey|greetings|howdy|good\s+(?:morning|afternoon|evening|night)|how\s+are\s+you|who\s+are\s+you|what\s+is\s+your\s+name|what('?s|\s+is)\s+up|thank\s+you|thanks|bye|goodbye|see\s+you|help\s+me|tell\s+me\s+a\s+joke)\b[^\?]*[\?!.]*$", re.I),
    re.compile(r"^\s*(write|create|compose)\s+(?:a\s+|an\s+)?(?:poem|story|song|essay|joke|code|script)\b.*", re.I),
    re.compile(r"^\s*(explain|tell me about|what is|how do|how does|why is)\s+(?!(?:the\s+)?(?:weather|temperature|forecast|time|date|news|happening|current|latest|today|tomorrow)).+", re.I),
]

# Capability inquiries about real-time abilities (web search, time, weather)
_CAPABILITY_PATTERNS = [
    re.compile(r"\b(?:can\s+you|are\s+you\s+able\s+to|do\s+you\s+have|can\s+we)\s+(?:do\s+)?(?:web\s+search(?:es)?|search\s+the\s+web|browse\s+the\s+web|access\s+(?:the\s+)?time|check\s+(?:the\s+)?time|tell\s+(?:the\s+)?time|weather\s+access|real-?time\s+access)\b", re.I),
    re.compile(r"\b(?:web\s+search(?:es)?\s+and\s+time\s+access|time\s+access\s+and\s+web\s+search)\b", re.I),
    re.compile(r"\b(?:can\s+you\s+(?:access\s+the\s+time|search\s+the\s+web))\b", re.I),
]

_TIME_PATTERNS = [
    re.compile(r"\bwhat\s+(?:is|['’]s)\s+(?:the\s+)?(?:current\s+)?time\b", re.I),
    re.compile(r"\bwhat\s+time\s+(?:is\s+it|now)\b", re.I),
    re.compile(r"\bwhat\s+time\b", re.I),
    re.compile(r"\btell\s+(?:me\s+)?(?:the\s+)?(?:current\s+)?time\b", re.I),
    re.compile(r"\bcheck\s+(?:the\s+)?(?:current\s+)?time\b", re.I),
    re.compile(r"\bcurrent\s+time\b", re.I),
    re.compile(r"\btime\s+now\b", re.I),
    re.compile(r"\btime\s+(?:in|at|for)\s+([a-zA-Z\s]+)", re.I),
    re.compile(r"\bwhat\s+(?:is|['’]s)\s+(?:the\s+)?(?:current\s+)?date\b", re.I),
    re.compile(r"\bwhat\s+day\s+(?:is\s+it|today)\b", re.I),
    re.compile(r"\btoday['’]?s\s+date\b", re.I),
    re.compile(r"\bcurrent\s+date\b", re.I),
    re.compile(r"\btime\s+access\b", re.I),
    re.compile(r"\baccess\s+(?:the\s+)?time\b", re.I),
]

_WEATHER_PATTERNS = [
    re.compile(r"\bweather\b", re.I),
    re.compile(r"\btemperature\b", re.I),
    re.compile(r"\bforecast\b", re.I),
    re.compile(r"\bwill\s+it\s+rain\b", re.I),
    re.compile(r"\bis\s+it\s+raining\b", re.I),
    re.compile(r"\bhumidity\b", re.I),
    re.compile(r"\bhow\s+hot\b", re.I),
    re.compile(r"\bhow\s+cold\b", re.I),
]

def extract_live_location(text: str) -> Optional[str]:
    m = re.search(r"\b(?:in|at|for)\s+([a-zA-Z\s]+?)(?:\?|$|\.|,|and\b)", text, re.I)
    if m:
        loc = m.group(1).strip()
        loc = re.sub(r"\b(tomorrow|today|weather|forecast|temperature|the|my location|here|outside|now)\b", "", loc, flags=re.I).strip()
        loc = re.sub(r"\s+", " ", loc)
        if loc and loc.lower() not in ("here", "my location", "outside", "now", "today"):
            return loc.split(" and ")[0].split(" or ")[0].strip()
    return None


class LiveToolResult:
    def __init__(
        self,
        tool_name: str,
        context_text: str,
        status_message: str,
        latency_ms: float = 0.0,
        success: bool = True,
    ):
        self.tool_name = tool_name
        self.context_text = context_text
        self.status_message = status_message
        self.latency_ms = latency_ms
        self.success = success


class LiveToolRouter:
    """
    Zero-extra-LLM tool classifier and async executor for Live Voice.
    Evaluates queries via pattern routing in < 0.2ms.
    """

    @classmethod
    def classify_tools(cls, query: str) -> List[Tuple[str, Optional[str]]]:
        """
        Classifies query into 0, 1, or multiple independent tools.
        Returns list of (tool_name, tool_param) tuples.
        """
        q = (query or "").strip()
        if not q or len(q) < 2:
            return []

        # 1. Non-tool bypass for ordinary smalltalk / creative / jokes
        for pat in _SMALLTALK_PATTERNS:
            if pat.match(q):
                return []

        # 1.1 Check for capability inquiries
        for pat in _CAPABILITY_PATTERNS:
            if pat.search(q):
                return [("capabilities", None)]

        tools: List[Tuple[str, Optional[str]]] = []

        # 2. Check for Uploaded Document / RAG queries
        for pat in _RAG_PATTERNS:
            if pat.search(q):
                tools.append(("rag", None))
                break

        # 3. Check for Location queries
        for pat in _LOCATION_PATTERNS:
            if pat.search(q):
                tools.append(("location", None))
                break

        # 4. Check for Time queries
        matched_time = False
        for pat in _TIME_PATTERNS:
            if pat.search(q):
                matched_time = True
                loc = extract_live_location(q)
                tools.append(("time", loc))
                break

        # 5. Check for Weather queries
        matched_weather = False
        for pat in _WEATHER_PATTERNS:
            if pat.search(q):
                matched_weather = True
                loc = extract_live_location(q)
                if not loc:
                    m_w = re.search(r"weather\s+(?:in|at|for)?\s*([a-zA-Z\s]+)", q, re.I)
                    if m_w:
                        w_cand = m_w.group(1).strip()
                        w_cand = re.sub(r"\b(today|tomorrow|now|here|outside)\b", "", w_cand, flags=re.I).strip()
                        if w_cand:
                            loc = w_cand
                tools.append(("weather", loc))
                break

        # 6. Check for Web Search / Real-time Current Events
        is_explicit_news = bool(re.search(
            r"\b(search the web|search web|browse the web|google|search online|look up online|latest news|news today|happened today|what's happening in the world|current events|world news|search for)\b",
            q,
            re.I
        ))

        # Only evaluate general search_mode if no time/weather was triggered, or if news was explicitly requested
        has_time_or_weather = matched_time or matched_weather
        if is_explicit_news or not has_time_or_weather:
            search_mode, _ = determine_search_mode(q)
            if search_mode != SearchMode.NONE or is_explicit_news:
                if not any(t[0] == "web_search" for t in tools):
                    tools.append(("web_search", None))

        return tools

    @classmethod
    def classify(cls, query: str) -> Tuple[Optional[str], Optional[str]]:
        """Convenience method returning the first detected tool or (None, None)."""
        tools = cls.classify_tools(query)
        if tools:
            return tools[0]
        return None, None

    @classmethod
    async def execute_tools_concurrently(
        cls,
        tools: List[Tuple[str, Optional[str]]],
        query: str,
        user_id: Optional[str] = None,
        timeout_s: float = 8.0,
    ) -> List[LiveToolResult]:
        """
        Executes multiple independent tools in parallel via asyncio.gather.
        """
        if not tools:
            return []

        tasks = [
            cls.execute_tool(t_name, query, t_param, user_id, timeout_s)
            for t_name, t_param in tools
        ]
        return await asyncio.gather(*tasks, return_exceptions=False)

    @classmethod
    async def execute_tool(
        cls,
        tool_name: str,
        query: str,
        location: Optional[str] = None,
        user_id: Optional[str] = None,
        timeout_s: float = 8.0,
    ) -> LiveToolResult:
        """
        Executes the required tool asynchronously with a strict timeout and cache lookup.
        """
        t0 = time.time()
        logger.info(f"[LIVE_TOOL] Starting execution for tool={tool_name}, param={location or query}")

        try:
            if tool_name == "time":
                return await asyncio.wait_for(cls._execute_time(location), timeout=timeout_s)

            elif tool_name == "weather":
                return await asyncio.wait_for(cls._execute_weather(location), timeout=timeout_s)

            elif tool_name == "location":
                return await asyncio.wait_for(cls._execute_location(), timeout=timeout_s)

            elif tool_name == "rag":
                return await asyncio.wait_for(cls._execute_rag(user_id), timeout=timeout_s)

            elif tool_name == "web_search":
                return await asyncio.wait_for(cls._execute_web_search(query), timeout=timeout_s)

            elif tool_name == "capabilities":
                return await cls._execute_capabilities()

            return LiveToolResult(tool_name, "", "")

        except asyncio.TimeoutError:
            latency_ms = (time.time() - t0) * 1000
            logger.warning(f"[LIVE_TOOL] Tool {tool_name} timed out after {latency_ms:.1f}ms")
            if tool_name == "web_search":
                fallback_ctx = (
                    "[Note: Live web search is taking longer than expected. "
                    "Please answer the user's question directly and informatively using your foundational knowledge, "
                    "without saying that you are unable to answer.]"
                )
            else:
                fallback_ctx = f"[Note: Real-time {tool_name} service timed out. Tell user it is temporarily unavailable.]"
            return LiveToolResult(
                tool_name=tool_name,
                context_text=fallback_ctx,
                status_message="Live service timeout",
                latency_ms=latency_ms,
                success=False,
            )
        except Exception as e:
            latency_ms = (time.time() - t0) * 1000
            logger.error(f"[LIVE_TOOL] Tool {tool_name} failed: {e}", exc_info=True)
            if tool_name == "web_search":
                fallback_ctx = (
                    "[Note: Live web search is momentarily unavailable. "
                    "Please answer the user's question directly and informatively using your foundational knowledge.]"
                )
            else:
                fallback_ctx = f"[Note: Real-time {tool_name} service encountered an error. Tell user it is temporarily unavailable.]"
            return LiveToolResult(
                tool_name=tool_name,
                context_text=fallback_ctx,
                status_message="Live service error",
                latency_ms=latency_ms,
                success=False,
            )

    @classmethod
    async def _execute_time(cls, location: Optional[str]) -> LiveToolResult:
        t0 = time.time()
        time_data = await get_time_data(location)
        time_str = time_data.get("time", "")
        date_str = time_data.get("date", "")
        day_str = time_data.get("day", "")
        loc_str = time_data.get("location", "UTC")
        tz_str = time_data.get("timezone", "")

        context = (
            f"REAL-TIME TIME DATA:\n"
            f"- Location: {loc_str}\n"
            f"- Time: {time_str}\n"
            f"- Date: {day_str}, {date_str} (Timezone: {tz_str})\n"
            f"Instruction: State the current time directly in 1 natural conversational sentence."
        )
        latency_ms = (time.time() - t0) * 1000
        return LiveToolResult("time", context, "Checking the time...", latency_ms, True)

    @classmethod
    async def _execute_weather(cls, location: Optional[str]) -> LiveToolResult:
        t0 = time.time()
        target_loc = location or "Chennai"
        cache_key = f"weather_{target_loc.lower().strip()}"

        # Cache check
        now = time.time()
        if cache_key in _LIVE_CACHE:
            cached_time, cached_val = _LIVE_CACHE[cache_key]
            if now - cached_time < CACHE_TTL_WEATHER_S:
                logger.info(f"[LIVE_TOOL] Weather cache hit for {target_loc}")
                return LiveToolResult("weather", cached_val, "Getting weather...", (time.time() - t0) * 1000, True)

        ws = WeatherService()
        wdata = await ws.get_weather_by_city(target_loc, forecast_days=2)

        loc_name = wdata.get("location", target_loc)
        curr = wdata.get("current", {})
        temp = curr.get("temperature")
        cond = curr.get("condition")
        humidity = curr.get("humidity")
        wind = curr.get("wind_speed")
        rain_prob = curr.get("rain_probability")

        context = (
            f"REAL-TIME WEATHER DATA:\n"
            f"- Location: {loc_name}\n"
            f"- Condition: {cond}\n"
            f"- Temperature: {temp}°C (Humidity: {humidity}%, Wind: {wind} km/h, Rain chance: {rain_prob}%)\n"
            f"Instruction: Summarize the current weather for {loc_name} in 1 or 2 natural spoken sentences."
        )

        _LIVE_CACHE[cache_key] = (now, context)
        latency_ms = (time.time() - t0) * 1000
        return LiveToolResult("weather", context, f"Getting weather for {target_loc}...", latency_ms, True)

    @classmethod
    async def _execute_location(cls) -> LiveToolResult:
        t0 = time.time()
        cache_key = "user_ip_location"
        now = time.time()

        if cache_key in _LIVE_CACHE:
            cached_time, cached_val = _LIVE_CACHE[cache_key]
            if now - cached_time < CACHE_TTL_LOCATION_S:
                return LiveToolResult("location", cached_val, "Locating...", (time.time() - t0) * 1000, True)

        loc_data = await ip_fallback_location()
        if loc_data:
            city = loc_data.get("city", "Unknown")
            state = loc_data.get("state", "")
            country = loc_data.get("country", "")
            context = (
                f"ESTIMATED USER LOCATION:\n"
                f"- City: {city}, {state}, {country}\n"
                f"Instruction: State the user's estimated approximate location briefly in 1 conversational sentence."
            )
        else:
            context = "User location could not be determined via network lookup."

        _LIVE_CACHE[cache_key] = (now, context)
        latency_ms = (time.time() - t0) * 1000
        return LiveToolResult("location", context, "Determining location...", latency_ms, True)

    @classmethod
    async def _execute_rag(cls, user_id: Optional[str]) -> LiveToolResult:
        t0 = time.time()
        if not user_id:
            context = "No uploaded user documents found."
        else:
            all_texts = RAGService.get_all_cached_texts(user_id)
            if all_texts:
                context = (
                    f"USER'S UPLOADED DOCUMENTS CONTEXT:\n{all_texts[:1500]}\n"
                    f"Instruction: Answer the user's question directly based on their uploaded document in 1 or 2 spoken sentences."
                )
            else:
                context = "The user has not uploaded any documents in this session."

        latency_ms = (time.time() - t0) * 1000
        return LiveToolResult("rag", context, "Reading uploaded documents...", latency_ms, True)

    @classmethod
    async def _execute_web_search(cls, query: str) -> LiveToolResult:
        t0 = time.time()
        clean_q = re.sub(r"(?i)\b(search the web for|search for|search web|google|find out about|tell me about)\b", "", query).strip()
        clean_q = clean_q or query
        cache_key = f"web_{clean_q.lower()}"
        now = time.time()

        if cache_key in _LIVE_CACHE:
            cached_time, cached_val = _LIVE_CACHE[cache_key]
            if now - cached_time < CACHE_TTL_SEARCH_S:
                logger.info(f"[LIVE_TOOL] Web search cache hit for '{clean_q}'")
                return LiveToolResult("web_search", cached_val, "Searching the web...", (time.time() - t0) * 1000, True)

        res = None
        try:
            from app.services.retrieval.providers import provider_pool
            raw_results = await provider_pool.text(clean_q, limit=4)
            snippets = []
            for r in raw_results[:4]:
                clean_body = re.sub(r"https?://\S+", "", r.body).strip()
                if clean_body:
                    snippets.append(f"- {r.title}: {clean_body[:250]}")
            if snippets:
                res = "\n".join(snippets)
        except Exception as e:
            logger.warning(f"[LIVE_TOOL] Provider pool search failed, trying WebSearchService: {e}")

        if not res:
            try:
                searcher = WebSearchService(max_results=3)
                res = await searcher.search(clean_q, max_results=3)
            except Exception as e:
                logger.warning(f"[LIVE_TOOL] WebSearchService fallback failed: {e}")

        if res and res.strip():
            # Clean snippets for voice consumption (strip heavy markdown tables, links)
            clean_res = re.sub(r"\[.*?\]\(.*?\)", "", res)
            clean_res = re.sub(r"https?://\S+", "", clean_res)
            context = (
                f"CURRENT REAL-TIME WEB SEARCH RESULTS:\n{clean_res[:1000]}\n\n"
                f"Instruction: Using the live search results above, answer the user's question accurately in 1 or 2 natural spoken sentences. Do not read raw URLs."
            )
        else:
            context = (
                f"[Note: Real-time web search for '{clean_q}' returned no immediate articles. "
                f"Please answer the user's question directly and informatively using your foundational knowledge in 1 or 2 spoken sentences.]"
            )

        _LIVE_CACHE[cache_key] = (now, context)
        latency_ms = (time.time() - t0) * 1000
        return LiveToolResult("web_search", context, "Searching the web...", latency_ms, True)

    @classmethod
    async def _execute_capabilities(cls) -> LiveToolResult:
        context = (
            "HSBOT REAL-TIME SYSTEM CAPABILITIES STATUS:\n"
            "- Live Web Search: ACTIVE and FULLY FUNCTIONAL. You can search the live web for breaking news, current events, and live facts.\n"
            "- Live Time Access: ACTIVE and FULLY FUNCTIONAL. You have instant access to the exact current time, date, and world timezones.\n"
            "- Live Weather: ACTIVE and FULLY FUNCTIONAL. You can provide live weather and temperature for any city.\n"
            "Instruction: Confidently and enthusiastically tell the user in 1 or 2 natural spoken sentences that you DO have full live web search, current time access, and weather lookup capabilities. Invite them to test it right now."
        )
        return LiveToolResult("capabilities", context, "Confirming capabilities...", 0.0, True)
