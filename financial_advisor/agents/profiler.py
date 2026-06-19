"""Profiler agent — turns the vague request into a structured investor profile.

It uses the workhorse model with *structured output*: rather than returning free
text, the model must return data matching the InvestorProfile schema, which
LangChain validates. Temperature is 0 (the workhorse default) because this is
extraction, not creative generation.
"""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from financial_advisor.config import workhorse_llm
from financial_advisor.state import AgentState, InvestorProfile

from financial_advisor.agents_system_prompts import PROFILER_SYSTEM_PROMPT


def _format_value(value) -> str:
    """Render a single profile value readably, without referencing field names."""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return f"{value:,.0f}" if value.is_integer() else f"{value:,.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _summarize_profile(profile: InvestorProfile) -> tuple[str, str]:
    """Summarize whatever the profiler actually decoded — field by field — instead
    of a fixed capital/horizon/risk triple. Empty or unset fields are skipped, so a
    sparse request gives a short line and a detailed one a fuller line, and any new
    schema field (e.g. min_holdings) shows up automatically. `assumptions` is pulled
    out separately for the trace note.
    """
    data = profile.model_dump()
    assumptions = data.pop("assumptions", "") or "none"

    parts = []
    for field, value in data.items():
        if not value:                      # skip unset / empty / zero fields
            continue
        text = _format_value(value)
        if len(text) > 60:                 # keep verbose free-text from bloating the line
            text = text[:57] + "..."
        parts.append(f"{field}={text}")

    summary = ", ".join(parts) if parts else "no concrete details extracted"
    return summary, assumptions


def profiler_node(state: AgentState) -> dict:
    profiler = workhorse_llm().with_structured_output(InvestorProfile)

    profile: InvestorProfile = profiler.invoke([
        SystemMessage(content=PROFILER_SYSTEM_PROMPT),
        HumanMessage(content=state["user_request"]),
    ])

    summary, assumptions = _summarize_profile(profile)

    return {
        "investor_profile": profile,
        "messages": [AIMessage(content=f"[Profiler] {summary} | assumptions: {assumptions}")],
    }