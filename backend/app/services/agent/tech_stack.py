"""
tech_stack.py
Universal Technology Selection, Environment Detection, Technology Lock,
and Adaptive Requirement Discovery Engine for HSBot Agent Mode.
"""

import os
import shutil
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger("hsbot.agent.tech_stack")


class TargetPlatform(str, Enum):
    WEB_BROWSER = "web_browser"
    MOBILE_ANDROID = "mobile_android"
    MOBILE_IOS = "mobile_ios"
    MOBILE_CROSS_PLATFORM = "mobile_cross_platform"
    DESKTOP_CROSS_PLATFORM = "desktop_cross_platform"
    CLI_SYSTEM_TOOL = "cli_system_tool"
    BACKEND_API = "backend_api"
    DATA_SCIENCE_ML = "data_science_ml"
    EMBEDDED_IOT = "embedded_iot"
    STATIC_SITE = "static_site"
    BROWSER_EXTENSION = "browser_extension"


class ProgrammingLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    CSHARP = "csharp"
    KOTLIN = "kotlin"
    SWIFT = "swift"
    DART = "dart"
    HTML_CSS = "html_css"
    SHELL = "shell"
    SQL = "sql"


class FrameworkType(str, Enum):
    REACT = "react"
    VUE = "vue"
    SVELTE = "svelte"
    VITE_VANILLA = "vite_vanilla"
    CANVAS_2D_WEBGL = "canvas_2d_webgl"
    FASTAPI = "fastapi"
    FLASK = "flask"
    EXPRESS = "express"
    GIN = "gin"
    ACTIX = "actix"
    TAURI = "tauri"
    ELECTRON = "electron"
    FLUTTER = "flutter"
    REACT_NATIVE = "react_native"
    SPRING_BOOT = "spring_boot"
    DOTNET_CORE = "dotnet_core"
    STANDALONE_CLI = "standalone_cli"
    NONE_NATIVE = "none_native"


@dataclass
class TechStackSnapshot:
    """Immutable Technology Lock established before architectural implementation."""
    platform: TargetPlatform
    primary_language: ProgrammingLanguage
    secondary_languages: List[ProgrammingLanguage] = field(default_factory=list)
    framework: FrameworkType = FrameworkType.NONE_NATIVE
    runtime_environment: str = "host"
    package_manager: str = "npm"
    build_system: str = "vite"
    test_framework: str = "node:assert"
    rationale: str = ""
    trade_offs: List[str] = field(default_factory=list)
    is_locked: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform.value if isinstance(self.platform, Enum) else str(self.platform),
            "primary_language": self.primary_language.value if isinstance(self.primary_language, Enum) else str(self.primary_language),
            "secondary_languages": [l.value if isinstance(l, Enum) else str(l) for l in self.secondary_languages],
            "framework": self.framework.value if isinstance(self.framework, Enum) else str(self.framework),
            "runtime_environment": self.runtime_environment,
            "package_manager": self.package_manager,
            "build_system": self.build_system,
            "test_framework": self.test_framework,
            "rationale": self.rationale,
            "trade_offs": self.trade_offs,
            "is_locked": self.is_locked
        }


class EnvironmentDetector:
    """
    Detects which compilers, interpreters, and build toolchains are actually installed
    on the host system so the agent never assumes missing compilers exist.
    """
    _cache: Optional[Dict[str, bool]] = None

    @classmethod
    def get_installed_toolchains(cls) -> Dict[str, bool]:
        if cls._cache is not None:
            return cls._cache

        binaries = [
            "python", "python3", "node", "npm", "pnpm", "yarn",
            "cargo", "rustc", "go", "java", "javac", "mvn", "gradle",
            "gcc", "g++", "clang", "cmake", "dart", "flutter", "git"
        ]
        status: Dict[str, bool] = {}
        for b in binaries:
            path = shutil.which(b)
            status[b] = path is not None

        cls._cache = status
        return cls._cache

    @classmethod
    def is_available(cls, binary: str) -> bool:
        installed = cls.get_installed_toolchains()
        return installed.get(binary.lower(), False)


class TechnologyDecisionEngine:
    """
    Evaluates product requirements, platform compatibility, ecosystem maturity,
    and host toolchain availability to select the most appropriate technology stack.
    Strictly forbids blindly forcing React + FastAPI onto unrelated projects.
    """

    @classmethod
    def select_and_lock_stack(
        cls,
        prompt: str,
        domain_str: str,
        product_type_str: str,
        explicit_constraints: Optional[Dict[str, Any]] = None
    ) -> TechStackSnapshot:
        text = prompt.lower()
        constraints = explicit_constraints or {}
        env = EnvironmentDetector.get_installed_toolchains()

        # 1. Check for explicit user language/framework requests
        if any(w in text for w in ["in rust", "using rust", "cargo"]):
            return TechStackSnapshot(
                platform=TargetPlatform.CLI_SYSTEM_TOOL if "cli" in text or "tool" in text else TargetPlatform.BACKEND_API,
                primary_language=ProgrammingLanguage.RUST,
                framework=FrameworkType.ACTIX if "api" in text or "web" in text else FrameworkType.STANDALONE_CLI,
                package_manager="cargo",
                build_system="cargo build",
                test_framework="cargo test",
                rationale="Explicit user request for Rust systems programming.",
                trade_offs=["High memory safety & performance", "Requires rustc/cargo toolchain"]
            )

        if any(w in text for w in ["in golang", "in go", "using go"]):
            return TechStackSnapshot(
                platform=TargetPlatform.CLI_SYSTEM_TOOL if "cli" in text else TargetPlatform.BACKEND_API,
                primary_language=ProgrammingLanguage.GO,
                framework=FrameworkType.GIN if "api" in text or "backend" in text else FrameworkType.STANDALONE_CLI,
                package_manager="go mod",
                build_system="go build",
                test_framework="go test",
                rationale="Explicit user request for Go concurrency and compiled binaries.",
                trade_offs=["Fast startup and compilation", "Simple deployment"]
            )

        if any(w in text for w in ["in python", "using python", "fastapi", "flask", "django"]):
            framework = FrameworkType.FLASK if "flask" in text else FrameworkType.FASTAPI
            return TechStackSnapshot(
                platform=TargetPlatform.BACKEND_API if "api" in text or "backend" in text else (TargetPlatform.DATA_SCIENCE_ML if "ml" in text or "data" in text else TargetPlatform.CLI_SYSTEM_TOOL),
                primary_language=ProgrammingLanguage.PYTHON,
                framework=framework,
                package_manager="pip",
                build_system="python -m build",
                test_framework="pytest",
                rationale="Python chosen for high developer velocity and extensive library ecosystem.",
                trade_offs=["Interpreted runtime", "Broadest data & AI interoperability"]
            )

        # 2. CLI / Systems Tool
        if any(w in text for w in ["cli tool", "command line tool", "terminal backup", "terminal utility", "shell script"]):
            return TechStackSnapshot(
                platform=TargetPlatform.CLI_SYSTEM_TOOL,
                primary_language=ProgrammingLanguage.PYTHON if env.get("python", True) else ProgrammingLanguage.JAVASCRIPT,
                framework=FrameworkType.STANDALONE_CLI,
                package_manager="pip",
                build_system="python setup.py",
                test_framework="pytest",
                rationale="Command-line interface with argument parsing, terminal formatting, and automated exit codes.",
                trade_offs=["Zero GUI overhead", "Direct POSIX/Windows terminal integration"]
            )

        # 3. Mobile Application (Android / iOS / Cross-platform)
        if any(w in text for w in ["mobile app", "android app", "ios app", "flutter", "react native"]):
            return TechStackSnapshot(
                platform=TargetPlatform.MOBILE_CROSS_PLATFORM,
                primary_language=ProgrammingLanguage.DART if "flutter" in text else ProgrammingLanguage.TYPESCRIPT,
                framework=FrameworkType.FLUTTER if "flutter" in text else FrameworkType.REACT_NATIVE,
                package_manager="pub" if "flutter" in text else "npm",
                build_system="flutter build" if "flutter" in text else "npm run build",
                test_framework="flutter test" if "flutter" in text else "jest",
                rationale="Mobile cross-platform architecture targeting handheld touchscreens and mobile viewports.",
                trade_offs=["Cross-platform code sharing", "Native device bridge"]
            )

        # 4. Games (Canvas 2D / 60fps WebGL)
        if domain_str == "game" or "game" in text or "shootout" in text or "arcade" in text:
            return TechStackSnapshot(
                platform=TargetPlatform.WEB_BROWSER,
                primary_language=ProgrammingLanguage.JAVASCRIPT,
                secondary_languages=[ProgrammingLanguage.HTML_CSS],
                framework=FrameworkType.CANVAS_2D_WEBGL,
                package_manager="npm",
                build_system="vite",
                test_framework="node:assert",
                rationale="JavaScript Canvas 2D engine with 60fps requestAnimationFrame loop and Web Audio API synthesis.",
                trade_offs=["Zero plugin installation required", "Immediate cross-device web execution"]
            )

        # 5. Pure Backend Microservice / API
        if domain_str == "python_backend" or ("backend" in text and not any(w in text for w in ["frontend", "ui", "web page"])):
            return TechStackSnapshot(
                platform=TargetPlatform.BACKEND_API,
                primary_language=ProgrammingLanguage.PYTHON,
                framework=FrameworkType.FASTAPI,
                package_manager="pip",
                build_system="uvicorn",
                test_framework="pytest",
                rationale="FastAPI asynchronous ASGI microservice with Pydantic type validation and automated OpenAPI docs.",
                trade_offs=["High asynchronous I/O performance", "Lightweight footprint"]
            )

        # 6. Static Documentation / Website
        if any(w in text for w in ["static site", "landing page", "documentation site"]) and not any(w in text for w in ["app", "system", "dashboard", "store"]):
            return TechStackSnapshot(
                platform=TargetPlatform.STATIC_SITE,
                primary_language=ProgrammingLanguage.HTML_CSS,
                secondary_languages=[ProgrammingLanguage.JAVASCRIPT],
                framework=FrameworkType.VITE_VANILLA,
                package_manager="npm",
                build_system="vite build",
                test_framework="node:assert",
                rationale="Zero-runtime-overhead static HTML5/Tailwind layout for instantaneous global edge delivery.",
                trade_offs=["Maximum SEO and speed", "Client-side only state"]
            )

        # 7. Default Rich Web Application (Domain Adaptive)
        return TechStackSnapshot(
            platform=TargetPlatform.WEB_BROWSER,
            primary_language=ProgrammingLanguage.JAVASCRIPT,
            secondary_languages=[ProgrammingLanguage.HTML_CSS],
            framework=FrameworkType.VITE_VANILLA,
            package_manager="npm",
            build_system="vite",
            test_framework="node:assert",
            rationale="Modern web architecture with semantic HTML5, utility-first styling, and reactive JavaScript state machines.",
            trade_offs=["Immediate browser previewability", "Universal cross-platform compatibility"]
        )


@dataclass
class QuizQuestion:
    id: str
    question: str
    options: List[str]
    default_option: str
    rationale: str


class AdaptiveQuizEngine:
    """
    Identifies missing high-impact product decisions and generates an adaptive,
    concise 2-4 question quiz without asking trivial or redundant styling questions.
    """

    @classmethod
    def evaluate_and_generate_quiz(cls, prompt: str) -> List[QuizQuestion]:
        text = prompt.lower().strip()
        quiz: List[QuizQuestion] = []

        # 1. Underspecified Shopping / E-commerce
        if any(w in text for w in ["shopping", "store", "ecommerce", "buy things", "sell products"]) and not any(w in text for w in ["b2b", "marketplace", "boutique", "auction"]):
            quiz.append(QuizQuestion(
                id="Q-SHOP-TYPE",
                question="What type of shopping experience would you like to build?",
                options=[
                    "Curated Direct Storefront (Single brand catalog, cart, direct checkout)",
                    "Multi-Vendor Marketplace (Multiple seller stores with vendor commission)",
                    "B2B Wholesale Portal (Bulk pricing tiers and purchase order invoicing)"
                ],
                default_option="Curated Direct Storefront (Single brand catalog, cart, direct checkout)",
                rationale="High impact on database relational model and checkout settlement architecture."
            ))

        # 2. Platform Target Ambiguity
        if ("app" in text or "software" in text) and not any(w in text for w in ["web", "browser", "mobile", "ios", "android", "desktop", "cli"]):
            quiz.append(QuizQuestion(
                id="Q-PLATFORM",
                question="Which platform should be the primary deployment target?",
                options=[
                    "Responsive Web Application (Accessible instantly in all modern desktop & mobile browsers)",
                    "Command-Line Interface (High-efficiency terminal command tool)",
                    "Native Mobile Architecture (Touch-optimized mobile workflow)"
                ],
                default_option="Responsive Web Application (Accessible instantly in all modern desktop & mobile browsers)",
                rationale="High impact on programming language and user interface runtime environment."
            ))

        # 3. Authentication & User Accounts
        if any(w in text for w in ["system", "platform", "portal", "management", "hospital", "learning", "social"]) and not any(w in text for w in ["with auth", "no auth", "public", "login"]):
            quiz.append(QuizQuestion(
                id="Q-AUTH",
                question="Does this application require user authentication and role-based permissions?",
                options=[
                    "Yes — Multi-Role Accounts (Admin, Staff, and Client roles with secure session state)",
                    "No — Open Interactive Workspace (Frictionless access with client-persisted local storage)"
                ],
                default_option="No — Open Interactive Workspace (Frictionless access with client-persisted local storage)",
                rationale="Determines whether authentication middleware and session tokens are required."
            ))

        return quiz
