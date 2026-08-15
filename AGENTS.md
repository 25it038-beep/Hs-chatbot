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


## Status
Backend + Frontend both running. All 16 API tests pass. Frontend has "Thinking" pulse indicator while waiting for first streaming token from NVIDIA. Auth-protected CRUD works end-to-end via JWT tokens.

## Commands
- **Backend**: `cd backend && uvicorn app.main:app --reload`
- **Frontend**: `cd frontend && npm run dev`
- **Docker**: `docker compose up`
