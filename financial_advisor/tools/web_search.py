"""Web-search tool (Tavily) for the Researcher agent.

Wraps Tavily in a minimal tool exposing only `query` (so the model can't pass
invalid or over-restrictive params), and — for hardening — it NEVER raises: a
search failure comes back as a clean observation the agent can reason around.
"""
from langchain_core.tools import tool
from langchain_tavily import TavilySearch

_tavily = TavilySearch(max_results=5, search_depth="advanced", topic="general")


@tool
def web_search(query: str) -> str:
    """Search the web for current financial, market, and instrument information.

    Pass a single focused query string (e.g. 'EUR money market ETF options 2026').
    Returns the most relevant results.
    """
    try:
        return _tavily.invoke({"query": query})
    except Exception as exc:
        # Fail closed: a search failure becomes a clean observation, not a crash.
        return (
            f"Web search is temporarily unavailable ({type(exc).__name__}). "
            "Proceed using the market-data tool and your general knowledge; "
            "do not retry the search repeatedly."
        )