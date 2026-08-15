import re
from typing import Optional

from app.services.nvidia.config import TASK_PATTERNS, TASK_ROUTES


# ─────────────────────────────────────────────────────────────
# GPT-level intent + orchestration engine
#
# Understands the user's actual objective (not just keywords),
# supports multiple intents, derives workflows, and returns a
# structured decision with a confidence score.
# ─────────────────────────────────────────────────────────────

# Explicit verbs that create a NEW visual artifact
GEN_VERBS = r"create|generate|make|design|draw|render|illustrate|paint|sketch|produce|craft|compose"

# Visual artifacts — the object of generation
VISUAL_NOUNS = (
    r"\b(?:i[am]*g[e]*s?|pic[ture]*s?|photo(?:graph)?s?|art(?:work)?s?|posters?|logos?|banners?|"
    r"diagrams?|charts?|illustrations?|icons?|mockups?|wallpapers?|covers?|thumbnails?|drawings?|"
    r"paintings?|memes?|gifs?|3d render[s]?|3d model[s]?)\b"
)

# Verbs that RETRIEVE existing images
SEARCH_VERBS = r"show|find|search|get|give|fetch|locate"

# Existing-image nouns (retrieval)
RETRIEVAL_NOUNS = r"\b(?:i[am]*g[e]*s?|pictures?|photos?|pics?|photographs?|examples?|diagrams?|wallpapers?|screenshots?)\b"

# Technical topics that mention "image generation" but are NOT image requests
TECHNICAL_IMAGE_TOPIC = re.compile(
    r"\b(?:api|endpoint|function|code|library|sdk|program|script|app|application|tool|website|service|system|module|package|pipeline|workflow)\b"
    r"|image[- ]generation|generate images",
    re.I,
)
TECHNICAL_ASK = re.compile(
    r"how (?:do|can|would|should|to|does|did)|how to|explain how|write (?:a|the|me)|build (?:a|an|the)|"
    r"implement (?:a|an|the)|learn (?:how|to)|tutorial|guide for|what is the best way",
    re.I,
)

PROJECTIVE = re.compile(r"\b(it|this|that|these|those|them|one)\b", re.I)

RECENCY = [
    r"\btoday\b", r"\btomorrow\b", r"\byesterday\b", r"\btonight\b",
    r"\bnow\b", r"\bcurent\b", r"\bcurrent\b", r"\blatest\b", r"\brecent\b",
    r"\bbreaking\b", r"\bnews\b", r"\bheadline\b", r"\bupdate\b",
    r"\bweather\b", r"\bforecast\b", r"\btemperature\b",
    r"\bprice\b", r"\bprices\b", r"\bquote\b", r"\bquotes\b", r"\bstock\b",
    r"\bstocks\b", r"\bmarket\b", r"\bcrypto\b", r"\bbitcoin\b", r"\beth\b",
    r"\bfixtures\b", r"\bscore\b", r"\bresult\b", r"\bschedule\b",
    r"\bthis week\b", r"\bthis month\b", r"\bthis year\b",
    r"\bwhat happened\b", r"\bwhat's new\b", r"\bwhat is new\b",
    r"\bstatus of\b", r"\brelease\b", r"\bannouncement\b", r"\blaunch\b",
    r"\bversion\b", r"\bchange log\b", r"\bchangelog\b",
    r"\bper cent\b", r"\bpercent\b", r"%\b",
    r"\bwho (?:is|are|was|were) the (?:new |current |present )?(?:cm|chief minister|president|prime minister|pm|minister|mayor|governor|ceo|chairman|chairperson|secretary|director|captain|coach|leader|head|king|queen|winner)\b",
    r"\bwho (?:is|are|won|became|become|took over|replaced)\b",
    r"\bwho (?:won|is leading|is ahead)\b",
    r"\bcurrent (?:cm|chief minister|president|leader|status|price|rate|position)\b",
    r"\bnew (?:cm|government|law|policy|rule|update)\b",
]

ARITHMETIC = re.compile(
    r"(\d+(?:\.\d+)?\s*[+\-*/%^]\s*)+(\d+(?:\.\d+)?)|\b(calculate|compute|add|subtract|multiply|divide|sqrt|square root|percent(?:age)? of)\b",
    re.I,
)

TRANSLATION = re.compile(
    r"\btranslate\b.*\b(?:to|into)\b|\bhow (?:do you|do i) say\b.*\b(?:in|into)\b|\bwhat is\b.*\b(?:called|said)\b.*\b(?:in|into)\b",
    re.I,
)

SUMMARIZE = re.compile(r"\b(summarize|summarise|tl;?dr|give me the summary|short version)\b", re.I)

RESEARCH_PHRASE = re.compile(
    r"\b(explain|research|learn about|tell me about|what is|what are|how does|how do|compare|contrast|analyze)\b",
    re.I,
)

SHOW_IMAGES_TOO = re.compile(
    r"\b(?:and|also|plus)\b.*\b(?:show|include|with|get|find)\b.*\b(?:relevant\s+|some\s+|me\s+)?(?:images|pictures|photos)\b",
    re.I,
)


class AIRouter:
    """Intent classification + orchestration engine."""

    def classify(self, message: str, context: Optional[list[str]] = None) -> dict:
        """Return a structured routing decision for the message.

        Context = recent user messages (oldest → newest) used for
        pronoun resolution and follow-ups.
        """
        text = (message or "").strip().lower()
        decision = {
            "primary_intent": "normal_chat",
            "secondary_intents": [],
            "confidence": 0.65,
            "requires_web": False,
            "requires_images": False,
            "requires_image_generation": False,
            "requires_verification": False,
            "tools": [{"name": "normal_chat", "purpose": "Answer the user's question directly"}],
            "workflow": ["compose_response"],
        }

        if not text:
            return decision

        # ── Slash commands — explicit intent ──
        if re.match(r"^/(image|img|draw|generate-image)\b", text):
            return self._image_generation(0.98)

        # ── File / vision analysis ──
        if text.startswith("[file:") or text.startswith("[image:"):
            return self._file_analysis()
        if re.search(r"\b(what is in this image|describe this image|analyze this image|what do you see|ocr|extract text from image)\b", text):
            return self._vision(0.92)

        # ── Technical guard: "create an image-generation API" is NOT an image request ──
        if TECHNICAL_IMAGE_TOPIC.search(text) and (
            TECHNICAL_ASK.search(text) or re.search(r"\b(api|endpoint|function|code|library|sdk|program|script)\b", text)
        ):
            return self._coding(0.92)

        # ── Image generation: explicit creation verbs + visual artifact ──
        gen_verb = re.search(rf"\b(?:{GEN_VERBS})\b", text)
        visual = re.search(VISUAL_NOUNS, text)
        if gen_verb and visual:
            # "generate a diagram" → generation; "show me diagrams of" → search
            if re.search(rf"\b(?:{SEARCH_VERBS})\b", text) and not re.search(
                rf"\b(?:create|generate|make|design|render|illustrate|paint|sketch|produce)\b", text
            ):
                return self._image_search(0.92)
            return self._image_generation(0.95)

        # Pronoun follow-up with context: "create an image of it" / "make it futuristic"
        if gen_verb and PROJECTIVE.search(text) and context:
            for prev in reversed(context):
                prev_decision = self.classify(prev)
                if prev_decision["requires_image_generation"]:
                    return self._image_generation(0.9)
                if prev_decision["requires_images"]:
                    return self._image_search(0.9)
                if len(prev) > 12:
                    break

        # Bare draw/illustrate/paint/sketch + article: "draw a cat", "paint a sunset"
        if re.search(r"\b(?:draw|illustrate|paint|sketch)\b\s+(?:a|an|the|me)\b", text):
            return self._image_generation(0.9)

        # ── Combined research + images: "explain X and show images" ──
        if RESEARCH_PHRASE.search(text) and SHOW_IMAGES_TOO.search(text):
            return self._web_and_images(0.9)

        # ── Image search: retrieve existing images ──
        if re.search(rf"\b(?:{SEARCH_VERBS})\b.*{RETRIEVAL_NOUNS}", text):
            return self._image_search(0.92)
        # Noun-last form: "cristiano ronaldo images", "cat pictures", "dog photos"
        if re.search(r"[\w'\-\s]{2,}\s+(images?|pictures?|photos?|pics?|screenshots?)\s*$", text):
            return self._image_search(0.85)
        # "images of X", "photos of X", "examples of X"
        if re.search(rf"{RETRIEVAL_NOUNS}\s+(?:of|for|about)\s+\w+", text):
            return self._image_search(0.88)

        # ── Current information / web search ──
        if any(re.search(p, text) for p in RECENCY) or re.search(
            r"\b(search (?:the web|online|for)|look up|live info|real[- ]time|202\d)\b", text
        ):
            decision = self._web_research(0.85 if not re.search(r"\b(search|look up)\b", text) else 0.93)
            decision["secondary_intents"].append("knowledge_question")
            return decision

        # ── Coding / debugging ──
        if self._looks_coding(text):
            return self._coding(0.88)

        # ── Math / calculation ──
        if ARITHMETIC.search(text):
            d = self._calculation(0.9)
            return d

        # ── Translation ──
        if TRANSLATION.search(text):
            return self._translation(0.9)

        # ── Summarization ──
        if SUMMARIZE.search(text):
            return self._summarization(0.85)

        # ── Knowledge question ──
        if re.search(r"\b(what is|what are|who is|who are|why|how does|how do|explain|define|when did|where is)\b", text):
            decision = {
                "primary_intent": "knowledge_question",
                "secondary_intents": [],
                "confidence": 0.8,
                "requires_web": False,
                "requires_images": False,
                "requires_image_generation": False,
                "requires_verification": False,
                "tools": [{"name": "normal_chat", "purpose": "Answer from stable general knowledge"}],
                "workflow": ["compose_response"],
            }
            return decision

        return decision

    # ── Intent builders ──
    def _image_generation(self, confidence: float) -> dict:
        return {
            "primary_intent": "image_generation",
            "secondary_intents": [],
            "confidence": confidence,
            "requires_web": False,
            "requires_images": False,
            "requires_image_generation": True,
            "requires_verification": False,
            "tools": [{"name": "image_generation", "purpose": "Generate a new visual from the prompt (NVIDIA FLUX)"}],
            "workflow": ["enhance_prompt", "generate_image", "compose_response"],
        }

    def _image_search(self, confidence: float) -> dict:
        return {
            "primary_intent": "image_search",
            "secondary_intents": [],
            "confidence": confidence,
            "requires_web": False,
            "requires_images": True,
            "requires_image_generation": False,
            "requires_verification": True,
            "tools": [{"name": "image_search", "purpose": "Retrieve existing images from the web (Wikimedia Commons)"}],
            "workflow": ["extract_subject", "search_images", "verify_image_relevance", "compose_response"],
        }

    def _web_research(self, confidence: float) -> dict:
        return {
            "primary_intent": "web_research",
            "secondary_intents": ["current_information"],
            "confidence": confidence,
            "requires_web": True,
            "requires_images": False,
            "requires_image_generation": False,
            "requires_verification": True,
            "tools": [{"name": "web_search", "purpose": "Fetch up-to-date information from the web"}],
            "workflow": ["search_web", "extract_topic", "compose_response"],
        }

    def _web_and_images(self, confidence: float) -> dict:
        return {
            "primary_intent": "web_research",
            "secondary_intents": ["image_search"],
            "confidence": confidence,
            "requires_web": True,
            "requires_images": True,
            "requires_image_generation": False,
            "requires_verification": True,
            "tools": [
                {"name": "web_search", "purpose": "Research the requested topic"},
                {"name": "image_search", "purpose": "Find images directly related to the researched topic"},
            ],
            "workflow": ["search_web", "extract_topic", "search_images", "verify_image_relevance", "compose_response"],
        }

    def _coding(self, confidence: float) -> dict:
        return {
            "primary_intent": "coding",
            "secondary_intents": [],
            "confidence": confidence,
            "requires_web": False,
            "requires_images": False,
            "requires_image_generation": False,
            "requires_verification": False,
            "tools": [{"name": "code_generation", "purpose": "Write, fix, or explain code"}],
            "workflow": ["reason_code", "compose_response"],
        }

    def _file_analysis(self) -> dict:
        return {
            "primary_intent": "file_analysis",
            "secondary_intents": [],
            "confidence": 0.95,
            "requires_web": False,
            "requires_images": False,
            "requires_image_generation": False,
            "requires_verification": False,
            "tools": [{"name": "file_analysis", "purpose": "Analyze the referenced uploaded file"}],
            "workflow": ["resolve_file", "analyze", "compose_response"],
        }

    def _vision(self, confidence: float) -> dict:
        return {
            "primary_intent": "image_analysis",
            "secondary_intents": [],
            "confidence": confidence,
            "requires_web": False,
            "requires_images": False,
            "requires_image_generation": False,
            "requires_verification": False,
            "tools": [{"name": "vision_analysis", "purpose": "Analyze the provided image"}],
            "workflow": ["resolve_image", "vision_analyze", "compose_response"],
        }

    def _calculation(self, confidence: float) -> dict:
        return {
            "primary_intent": "calculation",
            "secondary_intents": ["mathematics"],
            "confidence": confidence,
            "requires_web": False,
            "requires_images": False,
            "requires_image_generation": False,
            "requires_verification": False,
            "tools": [{"name": "calculator", "purpose": "Compute the arithmetic expression"}],
            "workflow": ["evaluate_expression", "compose_response"],
        }

    def _translation(self, confidence: float) -> dict:
        return {
            "primary_intent": "translation",
            "secondary_intents": [],
            "confidence": confidence,
            "requires_web": False,
            "requires_images": False,
            "requires_image_generation": False,
            "requires_verification": False,
            "tools": [{"name": "normal_chat", "purpose": "Translate the user's text"}],
            "workflow": ["compose_response"],
        }

    def _summarization(self, confidence: float) -> dict:
        return {
            "primary_intent": "summarization",
            "secondary_intents": [],
            "confidence": confidence,
            "requires_web": False,
            "requires_images": False,
            "requires_image_generation": False,
            "requires_verification": False,
            "tools": [{"name": "summarization", "purpose": "Summarize the provided content"}],
            "workflow": ["resolve_content", "summarize", "compose_response"],
        }

    def _looks_coding(self, text: str) -> bool:
        for kw in TASK_PATTERNS["coding"]:
            if " " in kw:
                if kw in text:
                    return True
            elif re.search(rf"\b{re.escape(kw)}\b", text):
                return True
        if re.match(r"^(def |class |function |const |import |from |#|\/\/|<!--|SELECT |INSERT |UPDATE )", text):
            return True
        if re.search(r"\b(error|exception|traceback|stack trace|undefined|nan|typeerror|syntaxerror)\b.*\b(fix|debug|why|not working)\b", text):
            return True
        return False

    # ── Legacy single-task API (kept for backward compatibility) ──
    def detect_task(self, message: str, context: Optional[list[str]] = None) -> str:
        d = self.classify(message, context=context)
        if d["requires_image_generation"]:
            return "image_generation"
        if d["requires_images"]:
            return "web_images"
        if d["primary_intent"] in ("image_analysis", "file_analysis"):
            return "vision"
        if d["primary_intent"] in ("coding",):
            return "coding"
        if d["primary_intent"] in ("calculation", "mathematics") or d["requires_web"]:
            return "reasoning" if d["primary_intent"] in ("calculation", "mathematics") else "chat"
        return "chat"

    def get_best_model(self, task: str, preferred_model: Optional[str] = None) -> str:
        if preferred_model:
            return preferred_model
        route = TASK_ROUTES.get(task, TASK_ROUTES["chat"])
        return route["default"]

    def get_fallback_models(self, task: str) -> list[str]:
        route = TASK_ROUTES.get(task, TASK_ROUTES["chat"])
        return route.get("fallback", [])

    def get_model_for_message(
        self, message: str, preferred_model: Optional[str] = None, context: Optional[list[str]] = None
    ) -> tuple[str, str]:
        task = self.detect_task(message, context=context)
        model = self.get_best_model(task, preferred_model)
        return task, model


ai_router = AIRouter()