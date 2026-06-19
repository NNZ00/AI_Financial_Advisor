"""Builds and compiles the trading-agent graph.

A Supervisor routes through five specialists with a bounded reflection loop and
conditional re-grounding. STAGE 7 adds node-level resilience: every specialist is
wrapped so an unhandled failure (an API blip, a malformed structured-output
response) aborts the run with an honest error proposal instead of crashing
graph.invoke() — and without fabricating a proposal from defaults.
"""
import functools

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END

from financial_advisor.state import AgentState
from financial_advisor.agents.profiler import profiler_node
from financial_advisor.agents.researcher import researcher_node
from financial_advisor.agents.strategist import strategist_node
from financial_advisor.agents.critic import critic_node
from financial_advisor.agents.reporter import reporter_node

SPECIALISTS = ("profiler", "researcher", "strategist", "critic", "reporter")

# Cap the reflect-and-refine loop so it can never run forever.
MAX_REVISIONS = 5

# Shown to the user when a node fails unrecoverably. Honest, not fabricated.
_ABORT_MESSAGE = (
    "We're sorry — the system hit a temporary error while building your proposal "
    "and couldn't complete it. Please try again in a moment."
)


def resilient(node_fn):
    """Wrap a node so an unhandled exception aborts the run gracefully.

    On failure the node writes an honest error as `final_proposal`; the supervisor
    reads any set `final_proposal` as a terminal state and routes to FINISH. This
    keeps a transient model failure from crashing the whole graph, and never
    invents an allocation or proposal to paper over a failed reasoning step.
    """
    @functools.wraps(node_fn)
    def wrapper(state):
        try:
            return node_fn(state)
        except Exception as exc:
            return {
                "final_proposal": _ABORT_MESSAGE,
                "messages": [AIMessage(
                    content=f"[{node_fn.__name__}] ERROR: {type(exc).__name__} — aborting gracefully."
                )],
            }
    return wrapper


def supervisor_node(state: AgentState) -> dict:
    """Decompose-first routing, with a bounded reflection loop, conditional
    re-grounding, and a terminal check so an aborted run stops cleanly."""
    revisions = state.get("revision_count", 0)
    approved = state.get("critic_approved")          # None / True / False
    needs_research = state.get("needs_research", False)

    if state.get("final_proposal"):
        next_node = "FINISH"                          # proposal written, OR a node aborted
    elif not state.get("investor_profile"):
        next_node = "profiler"
    elif not state.get("research_findings"):
        next_node = "researcher"                      # initial broad research
    elif not state.get("proposed_allocation"):
        next_node = "strategist"                      # first allocation
    elif approved is None:
        next_node = "critic"                          # review the current allocation
    elif approved is False and revisions < MAX_REVISIONS and needs_research:
        next_node = "researcher"                      # re-ground before revising
    elif approved is False and revisions < MAX_REVISIONS:
        next_node = "strategist"                      # revise with existing evidence
    else:
        next_node = "reporter"                        # approved, or revision cap hit

    update = {"next_node": next_node}
    if next_node == "strategist" and state.get("proposed_allocation"):
        update["revision_count"] = revisions + 1
    return update


def route_from_supervisor(state: AgentState) -> str:
    return state["next_node"]


def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_node)            # pure routing — no wrap needed
    graph.add_node("profiler", resilient(profiler_node))
    graph.add_node("researcher", resilient(researcher_node))
    graph.add_node("strategist", resilient(strategist_node))
    graph.add_node("critic", resilient(critic_node))
    graph.add_node("reporter", resilient(reporter_node))

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "profiler": "profiler",
            "researcher": "researcher",
            "strategist": "strategist",
            "critic": "critic",
            "reporter": "reporter",
            "FINISH": END,
        },
    )
    for specialist in SPECIALISTS:
        graph.add_edge(specialist, "supervisor")

    return graph.compile(checkpointer=checkpointer)