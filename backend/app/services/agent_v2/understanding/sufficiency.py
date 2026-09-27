import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from app.services.agent_v2.core.contracts import (
    RequirementClass,
    AdaptiveQuestion,
    ProductSpecification
)

logger = logging.getLogger("hsbot.agent_v2.understanding")

class RequirementSufficiencyEngine:
    """
    Evaluates whether user prompt contains enough information to build the product
    to production quality before coding begins (§7, §8, §9, §10, §11).
    Classifies requirements into KNOWN, INFERRED, MISSING, AMBIGUOUS, CONFLICTING, OPTIONAL.
    """

    @classmethod
    def evaluate(cls, user_request: str) -> Tuple[bool, List[Dict[str, Any]], Optional[AdaptiveQuestion]]:
        """
        Returns: (is_sufficient, classified_requirements, highest_impact_question)
        """
        text = user_request.strip().lower()
        classified = []
        is_sufficient = True
        highest_impact_question: Optional[AdaptiveQuestion] = None

        # 1. Product Objective
        if len(text) < 5:
            classified.append({"field": "objective", "status": RequirementClass.MISSING, "detail": "Prompt is too short to discern product intent."})
            is_sufficient = False
        else:
            classified.append({"field": "objective", "status": RequirementClass.KNOWN, "detail": user_request[:120]})

        # 2. Target Platform (Web, Mobile, Desktop, CLI, IoT)
        has_platform = any(w in text for w in ["web", "mobile", "ios", "android", "desktop", "cli", "command line", "terminal", "iot", "api", "backend"])
        if has_platform:
            plat = "web"
            for p in ["mobile", "desktop", "cli", "terminal", "iot", "api"]:
                if p in text:
                    plat = "cli" if p == "terminal" else p
                    break
            classified.append({"field": "platform", "status": RequirementClass.KNOWN, "detail": plat})
        else:
            # If the domain is inherently visual or interactive, default to web, but for ambiguous products check
            classified.append({"field": "platform", "status": RequirementClass.INFERRED, "detail": "web (sensible default)"})

        # 3. Domain & Workflow
        # Detect broad categories with potential material ambiguity
        is_social = any(w in text for w in ["social network", "social media", "social platform", "social app"])
        is_ecommerce = any(w in text for w in ["store", "ecommerce", "e-commerce", "marketplace", "shop"])
        is_game = any(w in text for w in ["game", "football", "soccer", "arcade", "simulator", "rpg"])
        is_healthcare = any(w in text for w in ["health", "hospital", "patient", "clinic", "medical", "doctor"])

        # High impact question for generic social app
        if is_social and not any(w in text for w in ["feed", "forum", "chat", "media", "professional", "community"]):
            is_sufficient = False
            highest_impact_question = AdaptiveQuestion(
                question_id="Q-SOCIAL-TYPE",
                prompt="What is the primary interaction experience for this social platform?",
                options=[
                    "Public Social Feed with Posts, Likes & Comments",
                    "Direct Real-Time Messaging & Group Channels",
                    "Community Topic Forum with Discussion Boards",
                    "Visual Media-First Sharing Platform"
                ],
                recommended_default="Public Social Feed with Posts, Likes & Comments",
                can_skip=True
            )

        # High impact question for generic e-commerce if ambiguous
        elif is_ecommerce and not any(w in text for w in ["physical", "digital", "subscription", "rental", "clothing", "electronics", "cart", "checkout"]):
            is_sufficient = False
            highest_impact_question = AdaptiveQuestion(
                question_id="Q-ECOMMERCE-TYPE",
                prompt="What type of merchandise does this store showcase?",
                options=[
                    "Curated Consumer Products & Hardware",
                    "Digital Assets, Software & Subscriptions",
                    "Fashion, Apparel & Luxury Accessories",
                    "Multi-Vendor Marketplace"
                ],
                recommended_default="Curated Consumer Products & Hardware",
                can_skip=True
            )

        # High impact question for generic game
        elif is_game and not any(w in text for w in ["football", "soccer", "racing", "arcade", "snake", "pong", "tetris", "shooter", "platformer", "card", "board"]):
            is_sufficient = False
            highest_impact_question = AdaptiveQuestion(
                question_id="Q-GAME-GENRE",
                prompt="Which game genre best matches your vision?",
                options=[
                    "2D Canvas Sports Arena (e.g. Football / Penalty Shootout)",
                    "Retro Arcade Action (e.g. Space Shooter / Breakout)",
                    "Puzzle & Strategy Game (e.g. Snake / Match-3)",
                    "Interactive Simulator / Physics Sandbox"
                ],
                recommended_default="2D Canvas Sports Arena (e.g. Football / Penalty Shootout)",
                can_skip=True
            )

        return is_sufficient, classified, highest_impact_question

    @classmethod
    def generate_product_specification(
        cls,
        user_request: str,
        answers: Optional[Dict[str, str]] = None
    ) -> ProductSpecification:
        """
        Creates the formal ProductSpecification source of truth (§12).
        """
        text = user_request.strip().lower()
        ans = answers or {}

        # 1. Determine Product Name
        name_candidate = "OmniCraft Realization"
        if "football" in text or "soccer" in text:
            name_candidate = "Apex Premier Football Arena"
            domain = "game"
            platform = "web"
            core_wf = [
                "Aim target angle and charge shot power bar",
                "Execute curving ball kicks past dynamic goalkeeper",
                "Track live scoreboard, strikes, saves, and celebration animations",
                "Trigger instant replay or reset match"
            ]
            entities = ["Player", "Ball", "GoalKeeper", "GoalPost", "MatchScore"]
            features = [
                "Canvas 2D physics pitch with turf texture",
                "Mouse drag flick and keyboard angle controls",
                "Reactive goalkeeper AI with trajectory diving",
                "Auditory whistle cues and goal celebration banners"
            ]
        elif "hospital" in text or "health" in text or "patient" in text:
            name_candidate = "AegisHealth Care & Patient Triage System"
            domain = "healthcare"
            platform = "web"
            core_wf = [
                "Triage incoming emergency and outpatient admissions",
                "Track vitals (HR, BP, SpO2) with real-time alert thresholds",
                "Assign attending physicians and bed allocations",
                "Schedule medication regimens and discharge summaries"
            ]
            entities = ["Patient", "TriageRecord", "Physician", "BedAllocation", "Medication"]
            features = [
                "Emergency Triage Status Matrix with severity color tags",
                "Patient Profile Drawer with clinical history",
                "Live Vitals telemetry dashboard with warning badges",
                "Physician assignment & consultation scheduler"
            ]
        elif "ecommerce" in text or "store" in text or "shop" in text:
            name_candidate = "Nexus Prime Commerce Marketplace"
            domain = "ecommerce"
            platform = "web"
            core_wf = [
                "Explore catalog with dynamic category and price filtering",
                "Inspect product image gallery, specifications, and customer reviews",
                "Add items to sliding slide-over cart with quantity steppers",
                "Simulate multi-step checkout with coupon validation and order summary"
            ]
            entities = ["Product", "CartItem", "Category", "Order", "CustomerReview"]
            features = [
                "Facet filtering by price range and stock status",
                "Slide-over cart with persistent localStorage sync",
                "Fast interactive checkout modal with address & card validation",
                "Order confirmation receipt with order ID"
            ]
        elif "delivery" in text or "food" in text or "restaurant" in text:
            name_candidate = "QuickBite Gourmet Delivery Engine"
            domain = "food_delivery"
            platform = "web"
            core_wf = [
                "Browse local culinary restaurants with delivery estimates",
                "Customize meal options with ingredient modifiers",
                "Assemble cart with delivery fee and tip calculations",
                "Monitor 4-stage live order tracking with status updates"
            ]
            entities = ["Restaurant", "MenuItem", "Cart", "DeliveryOrder", "Courier"]
            features = [
                "Restaurant hero cards with ratings, cuisine badges, and distance",
                "Ingredient customization modal with dietary badges",
                "Interactive order status tracker (Confirmed -> Kitchen -> Transit -> Delivered)",
                "Cart slide-over drawer with instant subtotal updates"
            ]
        else:
            # Custom/Arbitrary product synthesis (§46)
            title_words = [w.capitalize() for w in re.findall(r"\b[a-zA-Z]{3,}\b", user_request)[:3]]
            name_candidate = " ".join(title_words) + " Studio" if title_words else "Autonomous Product Studio"
            domain = "custom_software"
            platform = "web"
            core_wf = [
                "Initialize interactive workspace with domain directives",
                "Execute primary user commands with real-time UI feedback",
                "Manage state transitions and persistent records",
                "Export production assets and verified outputs"
            ]
            entities = ["Workspace", "Command", "EntityRecord", "ExportArtifact"]
            features = [
                "Modular workspace layout matching product requirements",
                "Responsive interaction controls and status telemetry",
                "Instant search and filter over workspace entities",
                "Verified asset exporter and downloadable releases"
            ]

        # Apply user answers from adaptive quiz if provided
        if "Q-SOCIAL-TYPE" in ans:
            core_wf.append(f"Primary interaction: {ans['Q-SOCIAL-TYPE']}")
        if "Q-ECOMMERCE-TYPE" in ans:
            core_wf.append(f"Merchandise category: {ans['Q-ECOMMERCE-TYPE']}")
        if "Q-GAME-GENRE" in ans:
            core_wf.append(f"Gameplay style: {ans['Q-GAME-GENRE']}")

        return ProductSpecification(
            product_name=name_candidate,
            product_purpose=f"Realize complete production-grade application for: '{user_request}'",
            target_users=["End Users", "Domain Operators", "Administrators"],
            problem=f"Provide a dedicated, high-fidelity solution fulfilling: '{user_request}'",
            domain=domain,
            platform=platform,
            core_workflow=core_wf,
            features=features,
            entities=entities,
            user_actions=["Explore", "Interact", "Configure", "Save", "Export"],
            inputs=["User Controls", "Form Data", "Configuration Parameters"],
            outputs=["Interactive UI", "State Updates", "Downloadable Artifacts"],
            business_rules=["Zero placeholder stubs", "Real persistent state", "Domain-authentic workflows"],
            constraints={"responsive": True, "self_contained": True},
            integrations=[],
            ai_requirements=[],
            security_requirements=["No secret leaks", "Input sanitization"],
            performance_requirements=["Sub-second UI response", "Smooth 60fps animations"],
            data_requirements=["Local persistent storage", "JSON export"],
            deployment_requirements=["Single bundle / static deployable release"],
            testing_requirements=["Automated workflow invariants", "DOM element checks"]
        )
