import pytest
from app.services.agent.app_generator import (
    AppDomain,
    AppDomainClassifier,
    CodeBlockExtractor,
    UniversalAppSynthesizer
)

def test_app_domain_classifier():
    # 1. Game
    domain, meta = AppDomainClassifier.classify("Create an arcade space shooter game with high score")
    assert domain == AppDomain.GAME
    assert meta.get("genre") == "shooter"

    domain, meta = AppDomainClassifier.classify("build a 2D football game with controls")
    assert domain == AppDomain.GAME
    assert meta.get("genre") == "football"

    # 2. Dashboard
    domain, _ = AppDomainClassifier.classify("Create an executive SaaS analytics dashboard with metrics and charts")
    assert domain == AppDomain.DASHBOARD

    # 3. E-Commerce
    domain, _ = AppDomainClassifier.classify("Build an online ecommerce store with a shopping cart and checkout")
    assert domain == AppDomain.ECOMMERCE

    # 4. Kanban
    domain, _ = AppDomainClassifier.classify("Create a trello-style kanban sprint board")
    assert domain == AppDomain.KANBAN

    # 5. Canvas Drawing
    domain, _ = AppDomainClassifier.classify("Build a whiteboard drawing app with color palette")
    assert domain == AppDomain.CANVAS_DRAW

    # 6. Audio Synth
    domain, _ = AppDomainClassifier.classify("Build a synthesizer with piano keys and drum machine")
    assert domain == AppDomain.AUDIO_SYNTH

    # 7. Markdown Workspace
    domain, _ = AppDomainClassifier.classify("Create a markdown editor with live preview")
    assert domain == AppDomain.MARKDOWN_WORKSPACE

    # 8. Finance Budget
    domain, _ = AppDomainClassifier.classify("Create a personal budget expense tracker")
    assert domain == AppDomain.FINANCE_BUDGET

    # 9. Calculator
    domain, _ = AppDomainClassifier.classify("Build a scientific calculator")
    assert domain == AppDomain.CALCULATOR

    # 10. Python Backend
    domain, _ = AppDomainClassifier.classify("Create a FastAPI SQLite backend service")
    assert domain == AppDomain.PYTHON_BACKEND

    # 11. Universal Dynamic
    domain, _ = AppDomainClassifier.classify("Build a recipe book cooking app")
    assert domain == AppDomain.UNIVERSAL_DYNAMIC


def test_code_block_extractor_json():
    # Strategy 1: Valid JSON
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


def test_code_block_extractor_markdown_blocks():
    # Strategy 4: Markdown fences with headers
    sample_md = '''
Here is your application:

### `index.html`
```html
<!DOCTYPE html>
<html>
<body>App</body>
</html>
```

### `styles.css`
```css
body { background: black; }
```

### `script.js`
```javascript
alert("ready");
```
    '''
    files = CodeBlockExtractor.extract_files(sample_md)
    assert "index.html" in files
    assert "styles.css" in files
    assert "script.js" in files
    assert "App" in files["index.html"]


def test_code_block_extractor_truncated_json():
    # Strategy 2: Truncated JSON recovery
    truncated_json = '''
    {"files": [
      {"path": "index.html", "content": "<h1>Testing</h1>"},
      {"path": "styles.css", "content": "h1 { color: red; }"},
      {"path": "script.js", "content": "let x = 1;
    '''
    files = CodeBlockExtractor.extract_files(truncated_json)
    assert "index.html" in files
    assert "styles.css" in files
    assert "Testing" in files["index.html"]


def test_universal_app_synthesizer_all_domains():
    for domain in [
        AppDomain.GAME,
        AppDomain.DASHBOARD,
        AppDomain.ECOMMERCE,
        AppDomain.KANBAN,
        AppDomain.CANVAS_DRAW,
        AppDomain.AUDIO_SYNTH,
        AppDomain.MARKDOWN_WORKSPACE,
        AppDomain.FINANCE_BUDGET,
        AppDomain.CALCULATOR,
        AppDomain.PYTHON_BACKEND,
        AppDomain.UNIVERSAL_DYNAMIC
    ]:
        files = UniversalAppSynthesizer.synthesize(f"Create a test {domain.value} application", domain)
        assert len(files) >= 3
        if domain == AppDomain.PYTHON_BACKEND:
            assert "main.py" in files
        else:
            assert "index.html" in files
            assert "script.js" in files
            assert "package.json" in files


@pytest.mark.asyncio
async def test_agent_multiprovider_executor_fallback(monkeypatch):
    from app.services.agent.app_generator import AgentMultiProviderExecutor
    from app.config import settings

    # Force all external provider keys to None/empty to test synthesizer fallback in 0.01s
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "sambanova_api_key", None)
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "nvidia_api_keys", "")

    files, source = await AgentMultiProviderExecutor.generate_project(
        user_request="Build a retro arcade space shooter game with high score"
    )
    assert len(files) >= 4
    assert "index.html" in files
    assert "script.js" in files
    assert "styles.css" in files
    assert "package.json" in files
    assert "UniversalSynthesizer" in source


def test_morden_foot_ball_game_synthesis_and_execution(tmp_path):
    import subprocess
    from app.services.agent.prompt_understanding import PromptUnderstandingEngine

    engine = PromptUnderstandingEngine()
    raw_prompt = "verify that it can create a morden foot ball game"
    normalized = engine.normalize_prompt(raw_prompt)
    assert "modern" in normalized
    assert "football" in normalized

    domain, meta = AppDomainClassifier.classify(raw_prompt)
    assert domain == AppDomain.GAME
    assert meta.get("genre") == "football"

    files = UniversalAppSynthesizer.synthesize(raw_prompt, domain, meta)
    assert "index.html" in files
    assert "script.js" in files
    assert "styles.css" in files
    assert "package.json" in files
    assert "tests/test_app.js" in files

    # Verify modern football game specific features
    assert "Modern Football Pro" in files["index.html"]
    assert "CHAMPIONS CUP" in files["index.html"]
    assert "renderPitch" in files["script.js"]
    assert "renderGoal" in files["script.js"]
    assert "renderGoalkeeper" in files["script.js"]
    assert "renderBall" in files["script.js"]
    assert "curve" in files["script.js"]
    assert "GOOOOOAL" in files["script.js"]

    # Verify test suite executes cleanly with Node.js
    test_file = tmp_path / "test_app.js"
    test_file.write_text(files["tests/test_app.js"], encoding="utf-8")
    proc = subprocess.run(["node", str(test_file)], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "All Modern Football Pro tests PASSED successfully!" in proc.stdout


def test_any_web_application_synthesis():
    test_prompts = [
        ("Create a social media photo feed web application with likes and comments", AppDomain.UNIVERSAL_DYNAMIC),
        ("Build a fitness gym routine workout planner web app with calories and timer", AppDomain.UNIVERSAL_DYNAMIC),
        ("Create a cryptocurrency portfolio tracker web application with live prices", AppDomain.UNIVERSAL_DYNAMIC),
        ("Build a collaborative cooking recipe book web app with search and categories", AppDomain.UNIVERSAL_DYNAMIC),
        ("Create a real estate apartment rental finder web application with filters", AppDomain.UNIVERSAL_DYNAMIC)
    ]

    for prompt, expected_domain in test_prompts:
        domain, meta = AppDomainClassifier.classify(prompt)
        assert domain == expected_domain, f"Prompt '{prompt}' failed domain classification"
        files = UniversalAppSynthesizer.synthesize(prompt, domain, meta)
        assert "index.html" in files
        assert "styles.css" in files
        assert "script.js" in files
        assert "package.json" in files
        assert "README.md" in files
        assert "tests/test_app.js" in files
        # Validate that HTML contains title and interactive structure
        assert "<!DOCTYPE html>" in files["index.html"]
        assert "<canvas" in files["index.html"] or "itemsGrid" in files["index.html"] or "container" in files["index.html"]

