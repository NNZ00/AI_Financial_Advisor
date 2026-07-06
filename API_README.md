# Financial Advisor — HTTP API + Web UI

A thin [FastAPI](https://fastapi.tiangolo.com/) layer that exposes the multi-agent
investment-proposal system (the `financial_advisor` LangGraph package) over HTTP,
plus a self-contained web interface to drive it from the browser.

The CLI entry point (`main.py`) still works exactly as before — this adds a web
layer on top of the same graph, without changing the agent code.

## What it does

The API wraps `build_graph().invoke(...)` — the same call the CLI makes. The graph
and its SQLite checkpointer are created once at startup and shared across requests.
Each `POST /advise` runs as an independent, persisted run keyed by a fresh
`thread_id`, which you can inspect afterwards.

## Setup

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-api.txt
```

`requirements-api.txt` holds the extra web dependencies (FastAPI + uvicorn) so the
CLI's own `requirements.txt` stays unchanged.

Then create a `.env` from `.env.example` and fill in your keys:

- `GOOGLE_API_KEY` — for the Gemini models
- `TAVILY_API_KEY` — for web research

## Run

```powershell
uvicorn api:app --reload
```

- **Web UI:** http://127.0.0.1:8000/ ← open this in a browser to use the system
- Interactive API docs (Swagger UI): http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

## Web UI

A self-contained single-page UI is served at `/` (source: `web/index.html`). Type a
request, click **Generate proposal**, and it renders the investor profile, the
allocation (donut + weighted table), the risk/suitability notes, and the full
proposal — organised into tabs. The `/advise` call is synchronous, so the page shows
a live elapsed timer while the agents work (typically 1–3 minutes). No build step:
it's plain HTML/CSS/JS served by FastAPI, same origin as the API (no CORS setup).

## Access protection (optional)

The app can require a shared password via HTTP Basic Auth. Set `APP_PASSWORD` (and
optionally `APP_USERNAME`, default `advisor`) in `.env`:

- **unset** → the app is open (convenient for local use);
- **set** → every route except `/health` requires the credentials, and the browser
  shows a native login prompt.

See [`GO_PUBLIC.md`](GO_PUBLIC.md) for exposing the app publicly over a tunnel.

## Endpoints

| Method | Path                 | Description                                         |
|--------|----------------------|-----------------------------------------------------|
| GET    | `/`                  | The web UI (HTML)                                   |
| GET    | `/api/info`          | Service info + endpoint list (JSON)                 |
| GET    | `/health`            | Liveness probe → `{"status": "ok"}` (never gated)   |
| POST   | `/advise`            | Run the full multi-agent analysis, return proposal  |
| GET    | `/runs/{thread_id}`  | Fetch a previously persisted run by id              |

### `POST /advise`

**Synchronous:** the response is held open until the whole multi-agent run finishes,
which can take from a few seconds to a few minutes.

Request body:

```json
{ "request": "I have 20,000 EUR to invest for retirement in ~30 years. I want long-term growth." }
```

Example (curl):

```bash
curl -X POST http://127.0.0.1:8000/advise \
  -H "Content-Type: application/json" \
  -d '{"request": "I have 20,000 EUR for retirement in ~30 years, long-term growth."}'
```

Response shape:

```json
{
  "thread_id": "…",
  "final_proposal": "…human-readable proposal…",
  "investor_profile": { "...": "..." },
  "allocation": { "reasoning": "...", "holdings": [ ... ], "risk_assessment": "...", "suitability_note": "..." },
  "revision_count": 0
}
```

### `GET /runs/{thread_id}`

Pass a `thread_id` returned by `/advise` to read that persisted run back from the
SQLite checkpoint DB (`financial_advisor.sqlite`, created on first run).
