"""Researcher agent — a ReAct agent that gathers market context using real tools.

Built with LangChain's `create_agent`. It interleaves reasoning with tool calls
until it has enough to write a brief. Because it's a compiled graph, this one
node is internally a graph of its own.
"""
from datetime import date

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

from financial_advisor.config import workhorse_llm
from financial_advisor.state import AgentState
from financial_advisor.tools.market_data import get_market_data
from financial_advisor.tools.web_search import web_search 

from financial_advisor.agents_system_prompts import RESEARCHER_SYSTEM_PROMPT

from langgraph.errors import GraphRecursionError

# Hard cap on the Researcher's ReAct loop. Normal research runs 3-6 tool rounds;
# LangGraph's default of 25 super-steps is loose enough that we once watched a
# re-grounding pass make 12 calls. 16 super-steps (~7 rounds) leaves legitimate
# research room while firmly stopping a runaway. Tunable.
RESEARCH_RECURSION_LIMIT = 16

_research_agent = create_agent(
    workhorse_llm(),
    tools=[web_search, get_market_data],
    system_prompt=RESEARCHER_SYSTEM_PROMPT,
)


def researcher_node(state: AgentState) -> dict:
    profile = state["investor_profile"]
    today = date.today().isoformat()
    re_grounding = state.get("needs_research", False)
    critique = state.get("critique", "")

    if re_grounding and critique:
        task = (
            f"Today's date is {today}. You earlier researched the market for this "
            f"investor. A risk reviewer has critiqued the proposed allocation, and the "
            f"fix needs NEW information:\n{critique}\n\n"
            "Do FOCUSED research to address exactly this — verify any newly suggested "
            "instruments with the market-data tool, find any requested alternatives, and "
            "report the real numbers. Do NOT redo the whole market review.\n\n"
            f"Investor profile:\n{profile.model_dump()}\n\nWrite a short addendum."
        )
    else:
        task = (
            f"Today's date is {today}. Research the current market to inform an "
            f"investment proposal for this investor profile:\n{profile.model_dump()}\n\n"
            "Use the tools for up-to-date information; do not rely on training knowledge "
            "for current conditions. Then write the research brief."
        )

    degraded = False
    try:
        result = _research_agent.invoke(
            {"messages": [HumanMessage(content=task)]},
            config={"recursion_limit": RESEARCH_RECURSION_LIMIT},
        )
        brief = result["messages"][-1].content
        tool_calls = sum(1 for m in result["messages"] if m.type == "tool")
    except GraphRecursionError:
        # Fail safe: hand the Strategist a flagged partial brief instead of crashing.
        degraded = True
        tool_calls = 0
        brief = (
            "[Research incomplete: the analyst reached its tool-call budget before "
            "finishing. Treat coverage as partial and prefer broad, well-established, "
            "liquid instruments.]"
        )

    note = " — INCOMPLETE (hit tool-call budget)" if degraded else ""
    note2 = "the strategist will use its base training to form a proposal" if degraded else "wrote the initial brief"

    if re_grounding:
        existing = state.get("research_findings", {}).get("summary", "")
        summary = f"{existing}\n\n[Re-grounding addendum addressing the critique]\n{brief}"
        return {
            "research_findings": {"summary": summary},
            "needs_research": False,
            "messages": [AIMessage(content=f"[Researcher] re-grounding: {tool_calls} tool call(s){note}; updated the brief.")],
        }
    return {
        "research_findings": {"summary": brief},
        "messages": [AIMessage(content=f"[Researcher] {tool_calls} tool call(s){note}; {note2}")],
    }