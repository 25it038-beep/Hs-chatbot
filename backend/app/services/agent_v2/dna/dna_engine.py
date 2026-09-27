import json
import re
import logging
from typing import Dict, List, Optional, Any, Set
from app.services.agent_v2.core.contracts import (
    ProductSpecification,
    ProductDNA
)
from app.services.agent.tech_stack import (
    TechnologyDecisionEngine,
    TechStackSnapshot
)

logger = logging.getLogger("hsbot.agent_v2.dna")

class CapabilityGraph:
    """
    Open-ended capability composition engine (§21).
    Decomposes a product into atomic capabilities to derive architecture and technology.
    """

    ALL_CAPABILITIES = {
        "web", "mobile", "desktop", "cli", "api", "database", "authentication",
        "authorization", "realtime", "websocket", "filesystem", "file-upload",
        "file-generation", "pdf", "docx", "pptx", "xlsx", "image", "audio",
        "video", "3d", "canvas", "webgl", "maps", "charts", "search", "ai",
        "rag", "vector-search", "background-jobs", "collaboration", "notifications",
        "payments", "simulation", "game-loop", "physics", "hardware", "iot",
        "code-execution", "terminal", "browser-automation", "analytics", "export"
    }

    @classmethod
    def extract_capabilities(cls, spec: ProductSpecification) -> Set[str]:
        text = f"{spec.product_name} {spec.product_purpose} {' '.join(spec.core_workflow)} {' '.join(spec.features)}".lower()
        words = set(re.findall(r'\b\w+\b', text))
        caps = {"web", "export"}

        if any(w in words for w in ["game", "football", "soccer", "arcade", "physics", "shoot"]):
            caps.update(["canvas", "game-loop", "physics", "audio"])
        if any(w in words for w in ["chart", "metric", "telemetry", "analytics", "budget", "finance"]):
            caps.update(["charts", "analytics"])
        if any(w in words for w in ["cli", "terminal"]) or "command line" in text:
            caps.update(["cli", "terminal", "code-execution"])
        if any(w in words for w in ["store", "cart", "checkout", "ecommerce", "payment"]):
            caps.update(["database", "payments"])
        if any(w in words for w in ["hospital", "patient", "medical", "records"]):
            caps.update(["database", "notifications"])
        if any(w in words for w in ["draw", "paint", "canvas", "whiteboard"]):
            caps.update(["canvas", "image"])
        if any(w in words for w in ["audio", "music", "synth"]):
            caps.update(["audio", "realtime"])

        return caps


class ProductDNAEngine:
    """
    Constructs the unique Product DNA and architectural blueprint (§13, §19, §20).
    Never reuses generic dashboard layouts for unrelated domains.
    """

    @classmethod
    def build_dna(
        cls,
        spec: ProductSpecification,
        user_request: str
    ) -> Tuple[ProductDNA, TechStackSnapshot]:
        # 1. Dynamic Technology Selection (§20)
        tech_stack = TechnologyDecisionEngine.select_and_lock_stack(
            prompt=user_request,
            domain_str=spec.domain,
            product_type_str="web_app"
        )

        caps = CapabilityGraph.extract_capabilities(spec)

        # 2. Design Visual Identity according to Domain (§22)
        if "healthcare" in spec.domain:
            visual_identity = {
                "visual_direction": "Clinical, reassuring, high contrast triage status indicators",
                "color_palette": {"primary": "#0284c7", "accent": "#ef4444", "surface": "#0f172a"},
                "layout_archetype": "triage_board_and_patient_drawer",
                "typography": "Clean sans-serif with high-contrast medical badges"
            }
            interaction_model = "triage_status_matrix_and_patient_drawer"
        elif "game" in spec.domain or "canvas" in caps:
            visual_identity = {
                "visual_direction": "Arcade Arena / Pitch styling with neon HUD accents and glow states",
                "color_palette": {"primary": "#10b981", "accent": "#f59e0b", "surface": "#020617"},
                "layout_archetype": "canvas_game_arena",
                "typography": "Chunky modern sans-serif with monospace scoreboard numbers"
            }
            interaction_model = "canvas_game_loop_and_keyboard_controls"
        elif "ecommerce" in spec.domain:
            visual_identity = {
                "visual_direction": "Refined retail showcase with high-res card grid and slide-over cart",
                "color_palette": {"primary": "#2563eb", "accent": "#f97316", "surface": "#0f172a"},
                "layout_archetype": "product_grid_and_slideover_cart",
                "typography": "Editorial serif headers with clean modern sans-serif body"
            }
            interaction_model = "filter_grid_and_slideover_cart"
        else:
            visual_identity = {
                "visual_direction": "Clean, focused, domain-authentic interface with responsive split view",
                "color_palette": {"primary": "#3b82f6", "accent": "#10b981", "surface": "#0f172a"},
                "layout_archetype": "modular_workspace_panels",
                "typography": "Modern system sans-serif"
            }
            interaction_model = "command_workspace_and_records"

        # 3. Assemble Product DNA (§13)
        dna = ProductDNA(
            identity=spec.product_name,
            purpose=spec.product_purpose,
            audience=spec.target_users,
            core_experience=visual_identity["visual_direction"],
            workflow=spec.core_workflow,
            feature_model={"features": spec.features, "capabilities": list(caps)},
            information_architecture={"entities": spec.entities, "actions": spec.user_actions},
            navigation=[f"#{f.lower().replace(' ', '-')}" for f in spec.features[:4]],
            interaction_model=interaction_model,
            visual_identity=visual_identity,
            technology=tech_stack.to_dict(),
            architecture={
                "pattern": "Client-State Reactive Workspace",
                "components": spec.features,
                "data_flow": "User Interaction -> State Machine -> Persistent Storage -> UI Render"
            },
            data_model={"entities": spec.entities},
            integrations=spec.integrations,
            testing_strategy=f"Automated DOM invariant testing via {tech_stack.test_framework}",
            deployment_strategy="Self-contained production package with static HTML/JS/CSS distribution"
        )

        return dna, tech_stack
