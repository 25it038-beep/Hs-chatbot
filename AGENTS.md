# HSBot - Project Context

## What is HSBot?
Multi-provider AI chat assistant with RAG (Retrieval-Augmented Generation), file upload support, and a Tauri 2 desktop wrapper. Users can chat with various LLMs from a single interface, manage chat histories, and get AI answers grounded in uploaded documents.

## Tech Stack
- **Backend**: Python FastAPI, SQLAlchemy 2.0, SQLite/PostgreSQL, Celery, Redis
- **Vector Store**: Qdrant
- **AI Providers**: NVIDIA NIM, OpenAI, Anthropic, Google Gemini, Ollama, OpenRouter, LM Studio, Azure OpenAI, SambaNova (fast default)
- **Frontend**: React 19, TypeScript, Vite 6, Tailwind CSS 4, Zustand, Radix UI, Clerk Auth (`@clerk/clerk-react`)
- **Authentication**: Clerk Authentication (`VITE_CLERK_PUBLISHABLE_KEY`) as primary default, with fallback JWT auth

## Key Structure
- `backend/app/` - FastAPI server (main.py, config.py, database.py, models/, schemas/, api/, services/, middleware/)
- `frontend/src/` - React SPA (pages/, components/, stores/, lib/, types/)
- `desktop/` - Tauri 2 shell
- `scripts/` - setup.ps1, start.ps1

## Verified Working
### Backend APIs (16/16 PASS)
- `GET /api/health` - Health check
- `POST /api/auth/register` + `POST /api/auth/login` - JWT auth (requires `username` + `email` + `password`)
- `POST /api/nvidia/chat` - NVIDIA chat (streaming + non-streaming) with auto-route
- `GET /api/nvidia/route` - Task detection router (query param: `message`)
- `POST /api/nvidia/embeddings` - text embeddings via NV-Embed v1 (4096 dim)
- `GET /api/models` + `GET /api/models/nvidia` - Model listings
- `POST /api/chats` + `GET /api/chats/{id}/messages` - Chat CRUD
- `POST /api/chats/messages` - Requires `message` + `chat_id` fields
- `DELETE /api/chats/{id}` - Delete chat
- `POST /api/files/upload` - File upload
- `GET /api/nvidia/usage` - Key manager stats

### NVIDIA Models Verified Working| Model Key | NVIDIA API ID | Response Time |
|-----------|---------------|---------------|
| `glm-5.2` | `z-ai/glm-5.2` | 5-165s (cold start ~165s) |
| `llama-3.3-70b` | `meta/llama-3.3-70b-instruct` | 265s (slow!) |
| `llama-3.1-70b` | `meta/llama-3.1-70b-instruct` | 4-5s |
| `mistral-large` | `mistralai/mistral-large-2-instruct` | 5-10s |
| `glm-coder` | `z-ai/glm-5.2` | same as glm-5.2 |
| `codestral` | `mistralai/codestral-22b-instruct-v0.1` | 10-20s |
| `flux-1-dev` | `black-forest-labs/flux.1-dev` | ~7-13s |
| `nv-embed-v1` | `nvidia/nv-embed-v1` | <5s |
| `nv-embedcode-7b` | `nvidia/nv-embedcode-7b-v1` | <5s |

### Removed / Non-existent Models
- `llama-4-maverick` - Not on NVIDIA
- `qwen-2.5-72b` - Not on NVIDIA
- `llama-code` - Not on NVIDIA

### SambaNova (fast default provider)
- Base URL: `https://api.sambanova.ai/v1` (OpenAI-compatible), enabled via `SAMBANOVA_API_KEY`
- **Default fast chat model: `DeepSeek-V3.2` (~4s)** — used for new chats
- Available models: `DeepSeek-V3.2` (~4s), `Meta-Llama-3.3-70B-Instruct` (~1s), `DeepSeek-V3.1` (~13s), `MiniMax-M2.7` (requires payment, 402), `gemma-4-31B-it` (~14s), `gpt-oss-120b`
- Frontend routes `provider === "sambanova"` through the generic `/api/chats/messages` stream; NVIDIA path (image gen, coding→thinking) is used when provider is `nvidia`

### Tavily (primary web search provider in the retrieval pipeline)
- Enabled via `TAVILY_API_KEY` (default: `tvly-dev-3PEQEw-...`) with automatic rotation to `TAVILY_FALLBACK_API_KEY` (default: `tvly-dev-4L9oxb-...`) on 401/403/429
- Lives in `backend/app/services/retrieval/providers.py` (`TavilyProvider`) — primary text+news provider, runs concurrently with DDGS + Wikipedia fallback (progressive completion: Tavily answered → 1.5s grace for secondaries → cancel stragglers)
- Returns scored results (`tavily_score` gets a small ranker bonus) + `published_date` for freshness ranking
- Config knobs: `TAVILY_TIMEOUT_S` (6), `RETRIEVAL_MAX_TAVILY_CONCURRENCY` (2), `RETRIEVAL_TAVILY_MAX_RESULTS` (10); verify key: `POST https://api.tavily.com/search` with `Authorization: Bearer <key>`

### Known Issues
- **First request to a model after backend restart is slow** (model cold start). Subsequent requests are faster.
- `llama-3.3-70b` takes ~265s for first token; may timeout (backend timeout currently 300s). Not recommended for default fallback.
- Wikipedia API + Wikimedia Commons may 403 from this IP after heavy usage (IP-level rate limit); DDGS is bursty — the pipeline degrades gracefully to Tavily results.
- **SambaNova `DeepSeek-V3.2` can 429 with "high demand"** — chat now auto-falls back to NVIDIA `llama-3.1-70b` (visible "SambaNova is busy..." note) so the user never gets an empty response. Fallback model is hardcoded — `NVIDIA_DEFAULT_CHAT_MODEL` must stay a live model id (was once `nemotron-3.5-lightning`, retired → 404).
- **Deploy verification**: `/api/health` returns `commit` (git short hash); deployed instance must match repo HEAD, otherwise it's a stale Render build (`env: development` = old build).

### Video retrieval (§26)
- `router.classify_video_intent()` -> `required | recommended | optional | not_needed`: explicit video words → required; procedural/demonstrative (how-to, tutorial, install, recipe...) → recommended; any knowledge query → optional; no search → not_needed.
- `retrieval/videos.py`: `VideoRetriever` — primary ddgs video search; fallback = web search (`{subject} video`) filtered to real video-platform hosts (youtube/vimeo/dailymotion/twitch/tiktok/bilibili...). Strict host-gated results preferred; only real URLs, never fabricated. `format_videos_md` caps at `RETRIEVAL_MAX_VIDEOS` (4), markdown `### Videos` list.
- Orchestrator: video search runs as its OWN task parallel to the fetch phase (never contends for Tavily/DDGS semaphores — an in-gather video job starved text search). Videos cached with the context; separated from text candidates.
- chat.py: required/recommended → blocking `with_videos=True` (anti-fabrication prompt note); optional → background task, appended after the answer within a 3s grace (non-blocking). Output order: Answer → Sources → Images → Videos.
- `ddgs.videos` often raises "No results found" from this IP — the host-gated web fallback is the real path; expect 1-4 videos, sometimes none.

### Selenium dynamic-page fallback (§27)
- **Never the default** — activates only when the fast chain (HTTP fetch → Tavily /extract) failed or returned too little text: `Search API -> cache -> HTTP fetch -> extract -> [Selenium] -> rerank -> LLM`.
- `retrieval/selenium_fetcher.py`: lazy bounded headless-Chrome pool (`SELENIUM_MAX_WORKERS`, each driver reused up to `SELENIUM_MAX_PAGES_PER_BROWSER`), Selenium Manager auto-drives chromedriver (selenium>=4.6, no manual download), explicit `WebDriverWait` for content selectors (no arbitrary sleeps), JS stays ON, images/notifications/extensions disabled.
- Timeouts: `SELENIUM_PAGE_LOAD_TIMEOUT_S` (8), `SELENIUM_TOTAL_TIMEOUT_S` (10, hard per-page via `asyncio.wait_for`), **startup has its own grace** (`SELENIUM_STARTUP_TIMEOUT_S` 30 — first driver start downloads chromedriver and must not burn the page budget; a timed-out startup is reclaimed so no driver leaks in_use). Slot lifecycle owned by the render thread's `finally` — a timing-out caller can never race another thread on the same driver. Max 3 browser fallbacks per request (`SELENIUM_MAX_FALLBACKS`); pool saturated → skip, never queue.
- Gating in `fetcher.py` `_selenium_candidate()`: only retryable failures (403/bot-blocked, network, timeout) and thin-HTTP bodies (< `SELENIUM_MIN_HTML_CHARS` 1500) qualify; NEVER 404/too-large/unsupported-type/unsafe-URL/5xx (a browser changes none of those). Reuses `is_safe_url` SSRF guard (DNS-verified), `extract_text`/`extract_meta`, and `RetrievalCache` keyed by URL sha1 with scope-based TTL (news/current = short).
- Public APIs: `fetch_dynamic(url, scope)` (browser only) and `fetch_resource(url, use_browser_fallback, scope)` (HTTP-first, browser fallback) → `{success, url, title, content, method: http|selenium, fallback_used, latency_ms, breakdown{http/selenium/extraction}, error}`. `get_stats()` counters for observability; `shutdown()` wired into `app/main.py` lifespan.
- Tests: `backend/tests/test_selenium_fetcher.py` (28 cases, browser mocked — no Chrome needed in CI; `pytest.ini` sets `asyncio_mode=auto`). Real-Chrome smoke verified locally: Wikipedia render 7.5k chars ~5s incl. driver start; page cache second call 0.0s; `example.com` correctly "thin-content" (142 chars < 200 min).
- Config knobs env-overridable: `SELENIUM_ENABLED`, `SELENIUM_HEADLESS`, `SELENIUM_BLOCK_IMAGES`, `SELENIUM_CONTENT_SELECTOR` ("article, main, [role=main], p, h1"), `SELENIUM_MIN_CONTENT_CHARS` (200). Missing selenium package degrades to disabled, never crashes.


## Status
Backend + Frontend both running. All 16 API tests pass. Frontend has "Thinking" pulse indicator while waiting for first streaming token from NVIDIA. Auth-protected CRUD works end-to-end via JWT tokens.

## Commands
- **Backend**: `cd backend && uvicorn app.main:app --reload`
- **Frontend**: `cd frontend && npm run dev`
- **Docker**: `docker compose up`
