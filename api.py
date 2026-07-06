"""FastAPI layer exposing the trading-agent graph over HTTP.

Wraps build_graph().invoke(...) in a small API plus a self-contained web UI. The
graph and its SQLite checkpointer are built once at startup and shared across
requests; each POST /advise is an independent, persisted run keyed by a fresh
thread_id, inspectable later via GET /runs/{thread_id}.

    uvicorn api:app --reload   ->   UI at http://127.0.0.1:8000/
"""
from typing import Optional
from pathlib import Path
import os
import secrets
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

from financial_advisor.graph import build_graph
from financial_advisor.persistence import make_checkpointer
from financial_advisor.state import Allocation, InvestorProfile


# Shared, process-wide objects, built once at startup (see lifespan).
_resources: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the graph + checkpointer at startup; close the DB at shutdown."""
    # Absolute path so the checkpoint DB lands next to this file regardless of cwd.
    db_path = str(Path(__file__).parent / "financial_advisor.sqlite")
    checkpointer = make_checkpointer(db_path)
    _resources["checkpointer"] = checkpointer
    _resources["graph"] = build_graph(checkpointer=checkpointer)
    try:
        yield
    finally:
        checkpointer.conn.close()


app = FastAPI(
    title="Financial Advisor API",
    description="HTTP interface to the multi-agent investment-proposal system.",
    version="1.0.0",
    lifespan=lifespan,
)

_WEB_DIR = Path(__file__).parent / "web"   # self-contained UI (web/index.html)


# --- Access protection: optional shared password via HTTP Basic Auth -----------
# APP_PASSWORD unset -> app is open (local use); set -> every route except
# /health requires it, and browsers show a native login prompt.
_APP_USERNAME = os.getenv("APP_USERNAME", "advisor")
_APP_PASSWORD = os.getenv("APP_PASSWORD", "")
_basic = HTTPBasic(auto_error=False)


def require_auth(credentials: Optional[HTTPBasicCredentials] = Depends(_basic)) -> None:
    """Enforce the shared password when APP_PASSWORD is set; otherwise a no-op."""
    if not _APP_PASSWORD:
        return
    ok = credentials is not None and (
        secrets.compare_digest(credentials.username, _APP_USERNAME)   # constant-time compare
        and secrets.compare_digest(credentials.password, _APP_PASSWORD)
    )
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing credentials.",
            headers={"WWW-Authenticate": "Basic"},   # makes the browser prompt for login
        )


# --- Request / response schemas ------------------------------------------------
class AdviseRequest(BaseModel):
    request: str = Field(
        ...,
        min_length=1,
        description="The investor's request, in free text.",
        examples=["I have 20,000 EUR to invest for retirement in ~30 years. "
                  "I'm comfortable with ups and downs and want long-term growth."],
    )


class AdviseResponse(BaseModel):
    thread_id: str = Field(description="Persisted run id; inspect later via GET /runs/{thread_id}.")
    final_proposal: str = Field(description="The human-readable investment proposal.")
    investor_profile: Optional[InvestorProfile] = Field(
        default=None, description="Structured profile the Profiler inferred from the request."
    )
    allocation: Optional[Allocation] = Field(
        default=None, description="The Strategist's structured portfolio (holdings, reasoning, risk)."
    )
    revision_count: int = Field(default=0, description="How many times the Critic sent it back for revision.")


# --- Endpoints -----------------------------------------------------------------
@app.get("/", include_in_schema=False, dependencies=[Depends(require_auth)])
def index() -> FileResponse:
    """Serve the self-contained web UI."""
    return FileResponse(_WEB_DIR / "index.html")


@app.get("/api/info", summary="Service info", dependencies=[Depends(require_auth)])
def info() -> dict:
    return {
        "service": "Financial Advisor API",
        "docs": "/docs",
        "endpoints": {"advise": "POST /advise", "inspect_run": "GET /runs/{thread_id}", "health": "GET /health"},
    }


@app.get("/health", summary="Liveness probe")
def health() -> dict:
    return {"status": "ok"}   # intentionally unprotected, for uptime checks


def _run_graph(user_request: str, thread_id: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    return _resources["graph"].invoke(
        {"user_request": user_request, "messages": []},
        config=config,
    )


@app.post("/advise", response_model=AdviseResponse, summary="Run the full multi-agent analysis",
          dependencies=[Depends(require_auth)])
async def advise(body: AdviseRequest) -> AdviseResponse:
    """Run the whole graph on the request and return the proposal.

    Synchronous: the response is held open until the run completes (seconds to a
    few minutes). The graph degrades gracefully internally, so a 500 here means an
    unexpected failure outside that safety net.
    """
    thread_id = str(uuid.uuid4())
    try:
        # graph.invoke blocks; run it off the event loop so other requests aren't stalled.
        result = await run_in_threadpool(_run_graph, body.request, thread_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {type(exc).__name__}")

    return AdviseResponse(
        thread_id=thread_id,
        final_proposal=result.get("final_proposal", ""),
        investor_profile=result.get("investor_profile"),
        allocation=result.get("proposed_allocation"),
        revision_count=result.get("revision_count", 0),
    )


@app.get("/runs/{thread_id}", response_model=AdviseResponse, summary="Fetch a past run by id",
         dependencies=[Depends(require_auth)])
def get_run(thread_id: str) -> AdviseResponse:
    """Read a previously persisted run back from the checkpoint DB."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = _resources["graph"].get_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail=f"No run found for thread_id '{thread_id}'.")
    values = snapshot.values
    return AdviseResponse(
        thread_id=thread_id,
        final_proposal=values.get("final_proposal", ""),
        investor_profile=values.get("investor_profile"),
        allocation=values.get("proposed_allocation"),
        revision_count=values.get("revision_count", 0),
    )
