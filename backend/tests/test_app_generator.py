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
