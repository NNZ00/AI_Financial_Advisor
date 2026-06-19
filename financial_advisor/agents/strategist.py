"""Strategist agent turns the profile informations and the research brief into a concrete allocation."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from financial_advisor.config import strategist_llm
from financial_advisor.state import AgentState, Allocation

from financial_advisor.agents_system_prompts import STRATEGIST_SYSTEM_PROMPT


def strategist_node(state: AgentState) -> dict:
    profile = state["investor_profile"]
    research = state.get("research_findings", {}).get("summary", "(no research available)")
    critique = state.get("critique", "")

    revision_note = ""
    if critique:
        revision_note = (
            f"\n\nA risk reviewer critiqued your previous allocation:\n{critique}\n"
            "Produce a REVISED allocation that addresses this critique."
        )

    strategist = strategist_llm().with_structured_output(Allocation)
    allocation: Allocation = strategist.invoke([
        SystemMessage(content=STRATEGIST_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Investor profile:\n{profile.model_dump()}\n\n"
            f"Research brief:\n{research}\n\n"
            f"Build the allocation now.{revision_note}"
        )),
    ])

    total = sum(h.weight_pct for h in allocation.holdings)
    if total > 0:
        for h in allocation.holdings:
            h.weight_pct = round(h.weight_pct / total * 100, 1)

    summary = ", ".join(f"{h.ticker or h.asset_class} {h.weight_pct:g}%" for h in allocation.holdings)
    return {
        "proposed_allocation": allocation,
        "critic_approved": None,   
        "messages": [AIMessage(content=f"[Strategist] {summary}")],
    }
