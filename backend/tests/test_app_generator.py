import pytest
import subprocess
from app.services.agent.app_generator import (
    AppDomain,
    ProductType,
    ProductRequirementSnapshot,
    AdaptiveRequirementEngine,
    AppDomainClassifier,
    CodeBlockExtractor,
    UniversalAppSynthesizer,
    AgentMultiProviderExecutor
)


def test_app_domain_classifier_all_domains():
    # 1. Healthcare
    domain, _ = AppDomainClassifier.classify("Build a hospital management system with patient records and appointments")
    assert domain == AppDomain.HEALTHCARE

    domain, _ = AppDomainClassifier.classify("Clinical patient triage and doctor schedule system")
    assert domain == AppDomain.HEALTHCARE

    # 2. Portfolio
    domain, _ = AppDomainClassifier.classify("Create a personal portfolio website for a software engineer")
    assert domain == AppDomain.PORTFOLIO

    # 3. Food Delivery
    domain, _ = AppDomainClassifier.classify("Build a food delivery restaurant ordering app with menus and tracking")
    assert domain == AppDomain.FOOD_DELIVERY

    # 4. Education
    domain, _ = AppDomainClassifier.classify("Create an online course academy platform with lessons and quizzes")
    assert domain == AppDomain.EDUCATION

    # 5. Travel
    domain, _ = AppDomainClassifier.classify("Build a luxury hotel and vacation stay booking app")
    assert domain == AppDomain.TRAVEL

    # 6. Social
    domain, _ = AppDomainClassifier.classify("Create a social community feed network with posts and likes")
    assert domain == AppDomain.SOCIAL

    # 7. Chat
    domain, _ = AppDomainClassifier.classify("Build a team messenger chat application with channels")
    assert domain == AppDomain.CHAT

    # 8. Real Estate
    domain, _ = AppDomainClassifier.classify("Create a real estate property listing marketplace with mortgage calculator")
    assert domain == AppDomain.REAL_ESTATE

    # 9. Recipe
    domain, _ = AppDomainClassifier.classify("Build a recipe book cooking studio app with ingredients and timer")
    assert domain == AppDomain.RECIPE

    # 10. Developer Tools
    domain, _ = AppDomainClassifier.classify("Build a code playground and JSON formatter tool")
    assert domain == AppDomain.DEVELOPER_TOOLS

    # 11. Games
    domain, meta = AppDomainClassifier.classify("Create an arcade space shooter game with high score")
    assert domain == AppDomain.GAME
    assert meta.get("genre") == "shooter"

    domain, meta = AppDomainClassifier.classify("build a 2D football game with controls")
    assert domain == AppDomain.GAME
    assert meta.get("genre") == "football"

    # 12. Dashboard
    domain, _ = AppDomainClassifier.classify("Create an executive SaaS analytics dashboard with metrics and charts")
    assert domain == AppDomain.DASHBOARD

    # 13. E-Commerce
    domain, _ = AppDomainClassifier.classify("Build an online ecommerce store with a shopping cart and checkout")
    assert domain == AppDomain.ECOMMERCE

    # 14. Kanban
    domain, _ = AppDomainClassifier.classify("Create a trello-style kanban sprint board")
    assert domain == AppDomain.KANBAN

    # 15. Canvas Drawing
    domain, _ = AppDomainClassifier.classify("Build a whiteboard drawing app with color palette")
    assert domain == AppDomain.CANVAS_DRAW

    # 16. Audio Synth
    domain, _ = AppDomainClassifier.classify("Build a synthesizer with piano keys and drum machine")
    assert domain == AppDomain.AUDIO_SYNTH

    # 17. Markdown Workspace
    domain, _ = AppDomainClassifier.classify("Create a markdown editor with live preview")
    assert domain == AppDomain.MARKDOWN_WORKSPACE

    # 18. Finance Budget
    domain, _ = AppDomainClassifier.classify("Create a personal budget expense tracker")
    assert domain == AppDomain.FINANCE_BUDGET

    # 19. Calculator
    domain, _ = AppDomainClassifier.classify("Build a scientific calculator")
    assert domain == AppDomain.CALCULATOR

    # 20. Python Backend
    domain, _ = AppDomainClassifier.classify("Create a FastAPI SQLite backend service")
    assert domain == AppDomain.PYTHON_BACKEND

    # 21. Universal Fallback
    domain, _ = AppDomainClassifier.classify("Build a custom plant watering schedule and soil moisture logger")
    assert domain == AppDomain.UNIVERSAL_DYNAMIC


def test_adaptive_requirement_snapshot_generation():
    snapshot = AdaptiveRequirementEngine.create_snapshot("Build a hospital management system.")
    assert snapshot.domain == AppDomain.HEALTHCARE
    assert snapshot.product_type == ProductType.HEALTHCARE_SYSTEM
    assert "Patients" in snapshot.key_entities or "Patient" in snapshot.key_entities
    assert len(snapshot.core_workflows) >= 3
    assert len(snapshot.navigation_items) >= 3

    snapshot_football = AdaptiveRequirementEngine.create_snapshot("Build a modern football game with physics and goal shootout")
    assert snapshot_football.domain == AppDomain.GAME
    assert snapshot_football.product_type == ProductType.GAME
    assert "Ball" in snapshot_football.key_entities
    assert "Goalkeeper" in snapshot_football.key_entities


def test_acceptance_prompt_a_hospital_management():
    prompt = "Build a hospital management system."
    domain, meta = AppDomainClassifier.classify(prompt)
    assert domain == AppDomain.HEALTHCARE

    snapshot = AdaptiveRequirementEngine.create_snapshot(prompt)
    files = UniversalAppSynthesizer.synthesize(prompt, domain, meta, snapshot)

    assert "index.html" in files
    assert "styles.css" in files
    assert "script.js" in files
    assert "package.json" in files
    assert "tests/test_app.js" in files

    html = files["index.html"]
    js = files["script.js"]

    # Verify clinical domain entities and elements
    assert "MetroHealth" in html or "Clinical" in html
    assert "admitPatientBtn" in html
    assert "bookApptBtn" in html
    assert "patients" in html
    assert "doctors" in html
    assert "prescriptions" in html
    assert "triage" in html
    assert "admitModal" in html

    # Verify JS clinical state logic
    assert "admitPatient" in js or "patients" in js
    assert "triageBadge" in js or "triage" in js


def test_acceptance_prompt_b_football_game(tmp_path):
    prompt = "Build a football game."
    domain, meta = AppDomainClassifier.classify(prompt)
    assert domain == AppDomain.GAME
    assert meta.get("genre") == "football"

    snapshot = AdaptiveRequirementEngine.create_snapshot(prompt)
    files = UniversalAppSynthesizer.synthesize(prompt, domain, meta, snapshot)

    html = files["index.html"]
    js = files["script.js"]

    assert "Modern Football Pro" in html
    assert "gameCanvas" in html
    assert "powerBar" in html
    assert "curveIndicator" in html

    assert "renderPitch" in js
    assert "renderGoal" in js
    assert "renderGoalkeeper" in js
    assert "renderBall" in js
    assert "isKeeperSave" in files["tests/test_app.js"]

    # Run Node tests
    test_file = tmp_path / "test_football.js"
    test_file.write_text(files["tests/test_app.js"], encoding="utf-8")
    proc = subprocess.run(["node", str(test_file)], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "All Modern Football Pro tests PASSED" in proc.stdout


def test_acceptance_prompt_c_ecommerce_storefront():
    prompt = "Build an e-commerce website."
    domain, meta = AppDomainClassifier.classify(prompt)
    assert domain == AppDomain.ECOMMERCE

    snapshot = AdaptiveRequirementEngine.create_snapshot(prompt)
    files = UniversalAppSynthesizer.synthesize(prompt, domain, meta, snapshot)

    html = files["index.html"]
    js = files["script.js"]

    assert "productsGrid" in html
    assert "cartToggleBtn" in html
    assert "cartCountBadge" in html
    assert "cart" in js


def test_acceptance_prompt_d_portfolio_website(tmp_path):
    prompt = "Build a portfolio website."
    domain, meta = AppDomainClassifier.classify(prompt)
    assert domain == AppDomain.PORTFOLIO

    snapshot = AdaptiveRequirementEngine.create_snapshot(prompt)
    files = UniversalAppSynthesizer.synthesize(prompt, domain, meta, snapshot)

    html = files["index.html"]
    js = files["script.js"]

    assert "Projects" in html
    assert "Skills" in html
    assert "Experience" in html
    assert "contactForm" in html
    assert "projectsGrid" in html

    test_file = tmp_path / "test_portfolio.js"
    test_file.write_text(files["tests/test_app.js"], encoding="utf-8")
    proc = subprocess.run(["node", str(test_file)], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "Portfolio" in proc.stdout


def test_acceptance_prompt_e_food_delivery(tmp_path):
    prompt = "Build a food delivery application."
    domain, meta = AppDomainClassifier.classify(prompt)
    assert domain == AppDomain.FOOD_DELIVERY

    snapshot = AdaptiveRequirementEngine.create_snapshot(prompt)
    files = UniversalAppSynthesizer.synthesize(prompt, domain, meta, snapshot)

    html = files["index.html"]
    js = files["script.js"]

    assert "CraveDash" in html or "Food" in html
    assert "restaurant" in html.lower() or "cuisine" in html.lower()
    assert "cartModal" in html
    assert "trackerModal" in html

    test_file = tmp_path / "test_food.js"
    test_file.write_text(files["tests/test_app.js"], encoding="utf-8")
    proc = subprocess.run(["node", str(test_file)], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "Food Delivery" in proc.stdout


def test_prompts_f_through_j_archetypes(tmp_path):
    prompts = [
        ("Build an online course learning platform.", AppDomain.EDUCATION, "EduSphere", "test_edu.js"),
        ("Build a travel booking application.", AppDomain.TRAVEL, "VoyageAir", "test_travel.js"),
        ("Build a social feed network with posts and likes.", AppDomain.SOCIAL, "Pulse", "test_social.js"),
        ("Build a team messenger chat application.", AppDomain.CHAT, "SyncTeam", "test_chat.js"),
        ("Build a real estate apartment rental marketplace.", AppDomain.REAL_ESTATE, "Haven", "test_re.js"),
        ("Build a recipe cooking studio app.", AppDomain.RECIPE, "FlavorCraft", "test_recipe.js"),
        ("Build a developer tools code playground.", AppDomain.DEVELOPER_TOOLS, "DevCraft", "test_dev.js")
    ]

    for prompt, expected_domain, brand_keyword, test_filename in prompts:
        domain, meta = AppDomainClassifier.classify(prompt)
        assert domain == expected_domain, f"Prompt '{prompt}' failed domain classification"

        snapshot = AdaptiveRequirementEngine.create_snapshot(prompt)
        files = UniversalAppSynthesizer.synthesize(prompt, domain, meta, snapshot)

        assert "index.html" in files
        assert "script.js" in files
        assert "tests/test_app.js" in files
        assert brand_keyword in files["index.html"]

        test_file = tmp_path / test_filename
        test_file.write_text(files["tests/test_app.js"], encoding="utf-8")
        proc = subprocess.run(["node", str(test_file)], capture_output=True, text=True)
        assert proc.returncode == 0, f"Node test failed for {prompt}: {proc.stderr}"


def test_no_template_contamination_and_distinct_identities():
    """Verify that different archetypes do not share identical templates or layouts."""
    prompts = {
        "healthcare": "Build a hospital management system.",
        "football": "Build a football game.",
        "ecommerce": "Build an e-commerce website.",
        "portfolio": "Build a portfolio website.",
        "food_delivery": "Build a food delivery application."
    }

    results = {}
    for key, prompt in prompts.items():
        domain, meta = AppDomainClassifier.classify(prompt)
        snapshot = AdaptiveRequirementEngine.create_snapshot(prompt)
        files = UniversalAppSynthesizer.synthesize(prompt, domain, meta, snapshot)
        results[key] = files

    # 1. Healthcare must NOT have canvas game or cart tray
    assert "gameCanvas" not in results["healthcare"]["index.html"]
    assert "cartTray" not in results["healthcare"]["index.html"]
    assert "admitPatientBtn" in results["healthcare"]["index.html"]

    # 2. Football must NOT have hospital patients or ecommerce cart
    assert "admitPatientBtn" not in results["football"]["index.html"]
    assert "productsGrid" not in results["football"]["index.html"]
    assert "gameCanvas" in results["football"]["index.html"]

    # 3. Portfolio must NOT have football canvas or hospital vitals
    assert "gameCanvas" not in results["portfolio"]["index.html"]
    assert "vitals" not in results["portfolio"]["index.html"]
    assert "skills" in results["portfolio"]["index.html"].lower()

    # 4. Food delivery must NOT have hospital triage or football keeper
    assert "keeper" not in results["food_delivery"]["script.js"]
    assert "triage" not in results["food_delivery"]["index.html"]
    assert "trackerModal" in results["food_delivery"]["index.html"]

    # 5. All generated index.html files must be mutually distinct
    html_contents = [files["index.html"] for files in results.values()]
    assert len(set(html_contents)) == len(html_contents), "Generated HTML templates must be completely unique"


def test_code_block_extractor():
    sample_json = '''
    {
      "files": [
        {"path": "index.html", "content": "<!DOCTYPE html><html><body><h1>Hello</h1></body></html>"},
        {"path": "styles.css", "content": "body { margin: 0; }"},
        {"path": "script.js", "content": "console.log('App ready');"}
      ]
    }
    '''
    files = CodeBlockExtractor.extract_files(sample_json)
    assert "index.html" in files
    assert "styles.css" in files
    assert "script.js" in files
    assert "Hello" in files["index.html"]


@pytest.mark.asyncio
async def test_agent_multiprovider_executor_fallback(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "sambanova_api_key", None)
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "nvidia_api_keys", "")

    files, source = await AgentMultiProviderExecutor.generate_project(
        user_request="Build a hospital patient management system"
    )
    assert len(files) >= 4
    assert "index.html" in files
    assert "MetroHealth" in files["index.html"] or "Clinical" in files["index.html"]
    assert "UniversalSynthesizer:healthcare" in source
