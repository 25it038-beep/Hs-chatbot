# HSBot - Project Context

## What is HSBot?
Multi-provider AI chat assistant with RAG (Retrieval-Augmented Generation), file upload support, and a Tauri 2 desktop wrapper. Users can chat with various LLMs from a single interface, manage chat histories, and get AI answers grounded in uploaded documents.

## Tech Stack
- **Backend**: Python FastAPI, SQLAlchemy 2.0, SQLite/PostgreSQL, Celery, Redis
- **Vector Store**: Qdrant
- **AI Providers**: NVIDIA NIM, OpenAI, Anthropic, Google Gemini, Ollama, OpenRouter, LM Studio, Azure OpenAI
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

### NVIDIA Models Verified Working
| Model Key | NVIDIA API ID | Response Time |
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

### Known Issues
- **First request to a model after backend restart is slow** (model cold start). Subsequent requests are faster.
- `llama-3.3-70b` takes ~265s for first token; may timeout (backend timeout currently 300s). Not recommended for default fallback.


## Status
Backend + Frontend both running. All 16 API tests pass. Frontend has "Thinking" pulse indicator while waiting for first streaming token from NVIDIA. Auth-protected CRUD works end-to-end via JWT tokens.

## Commands
- **Backend**: `cd backend && uvicorn app.main:app --reload`
- **Frontend**: `cd frontend && npm run dev`
- **Docker**: `docker compose up`
