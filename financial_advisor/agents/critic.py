"""Critic / Risk agent — an independent reviewer of the Strategist's allocation."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from financial_advisor.config import strategist_llm
from financial_advisor.state import AgentState
from financial_advisor.state import CriticVerdict

from financial_advisor.agents_system_prompts import CRITIC_SYSTEM_PROMPT


def critic_node(state: AgentState) -> dict:
    profile = state["investor_profile"]
    allocation = state["proposed_allocation"]

    critic = strategist_llm(temperature=0.0).with_structured_output(CriticVerdict)
    verdict: CriticVerdict = critic.invoke([
        SystemMessage(content=CRITIC_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Investor profile:\n{profile.model_dump()}\n\n"
            f"Proposed allocation:\n{allocation.model_dump()}\n\n"
            "Review it and return your verdict."
        )),
    ])

    approved = verdict.approved
    critique = verdict.critique
    needs_research = verdict.needs_research and not verdict.approved

    min_holdings = getattr(profile, "min_holdings", 0) or 0
    if min_holdings and len(allocation.holdings) < min_holdings:
        approved = False
        shortfall = (
            f"The investor explicitly requires at least {min_holdings} distinct holdings, "
            f"but this allocation has only {len(allocation.holdings)}. Add suitable, "
            f"diversified instruments to reach at least {min_holdings}."
        )
        critique = f"{critique}\n\n{shortfall}".strip() if critique else shortfall
        needs_research = True   # finding more good instruments likely needs a research pass

    status = "approved" if approved else "needs revision"
    regr = " (needs re-grounding)" if (not approved and needs_research) else ""
    detail = f": {critique}" if critique else ""
    return {
        "critic_approved": approved,
        "critique": critique,
        "needs_research": needs_research,
        "messages": [AIMessage(content=f"[Critic] {status}{regr}{detail}")],
    }
