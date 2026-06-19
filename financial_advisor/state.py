"""Shared state for the trading-agent graph."""

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from pydantic import BaseModel, Field

class InvestorProfile(BaseModel):
    """Structured investor profile the Profiler produces via structured output.

    The field descriptions are not just documentation — the LLM reads them when
    filling the schema, so they're worth writing carefully.
    """
    capital: float = Field(default=10_000, description="Amount to invest. If the user didn't state it, use this default and note it in assumptions.")
    currency: str = Field(default="USD", description="Currency code, e.g. 'USD' or 'EUR'. Default 'USD' if unstated.")
    time_horizon: str = Field(default="", description="Investment horizon expressed in the provided time unit. Do not assume if not provided.")
    risk_tolerance: str = Field(default="medium",
                                description="One of 'low', 'medium', 'high'. Infer from the request; default 'medium' when unclear. "
                                "A novice who 'doesn't know much' should NOT be assumed to want high risk.")
    goals: str = Field(default="", description="Investment goals: growth, income, capital preservation, etc. Infer from the request.")
    constraints: str = Field(default="", description="Constraints such as liquidity needs, sector exclusions, or ethical limits. Empty if none.")
    assumptions: str = Field(default="", description="Briefly list any values you assumed because the user didn't specify them.")
    min_holdings: int = Field(default=0,description="Minimum number of distinct holdings the investor explicitly requires ""(e.g. 'at least 6 products' -> 6). Use 0 when no minimum is stated.")
    max_holdings: int = Field(default=0,description="Maximum number of distinct holdings the investor explicitly requires ""(e.g. 'at most 10 products' -> 10). Use 0 when no maximum is stated.")


class Holding(BaseModel):
    asset: str = Field(description="Human-readable name, e.g. 'Global equity ETF (developed + emerging)'.")
    ticker: str = Field(default="", description="Ticker, e.g. 'VWCE'. Empty for cash.")
    asset_class: str = Field(description="e.g. 'equity', 'bond', 'cash', 'commodity'.")
    weight_pct: float = Field(description="Percentage of the portfolio (0-100). All weights must sum to 100.")
    rationale: str = Field(description="Why this instrument and this weight, tied to the investor profile.")


class Allocation(BaseModel):
    """The Strategist's proposed portfolio.

    `reasoning` is listed FIRST on purpose: the model fills fields in schema order,
    so reasoning-first forces it to think before it allocates — chain-of-thought
    baked into the structure.
    """
    reasoning: str = Field(description="Step-by-step reasoning: from horizon and risk capacity, to asset-class mix, to specific instruments and weights. Think here before deciding holdings.")
    holdings: list[Holding] = Field(description="The portfolio. Weights must sum to 100.")
    risk_assessment: str = Field(description="Reconcile the stated risk appetite with the actual risk capacity given the horizon. State the main risks and the expected volatility character.")
    suitability_note: str = Field(description="Honest note on whether the goal is realistic for this profile. If not, say so plainly and give the best honest alternative. Never promise returns.")


class CriticVerdict(BaseModel):
    """Structured verdict. `reasoning` first → think before ruling."""
    reasoning: str = Field(description="Step-by-step review of the allocation against the profile and sound portfolio principles.")
    approved: bool = Field(description="True only if the allocation is sound and defensible as-is; False if it has a material problem.")
    critique: str = Field(description="If not approved, specific and actionable feedback the strategist can act on. Empty string if approved.")
    needs_research: bool = Field(default=False, description="Set True ONLY if fixing your critique requires NEW external information — e.g. verifying or pricing an instrument not already in the research brief, or finding a requested alternative. Set False for purely structural fixes (rebalancing, reducing concentration) the strategist can make with instruments already researched.")

    
class AgentState(TypedDict):
    """The graph's shared state — the contract all agents collaborate through."""

    # The original, raw request from the user.
    user_request: str
    messages: Annotated[list[AnyMessage], add_messages]
    investor_profile: InvestorProfile   # written by the Profiler
    research_findings: dict             # written by the Researcher 
    proposed_allocation: Allocation     # written by the Strategist
    final_proposal: str                 # written by the Reporter

    # The Supervisor writes its routing decision here: the name of the next
    # node to run, or "FINISH" when the proposal is complete.
    next_node: str

    # The Critic/Risk agent's feedback on the proposed allocation. When it's
    # non-empty and not yet resolved, the Supervisor routes back to the
    # Strategist to revise.
    critique: str

    # How many times the allocation has been revised. The Supervisor uses this
    # to cap the loop (stop after N rounds) so reflection can't run forever —
    # the termination condition the planning paper's refine() step requires.
    revision_count: int

    # The Critic's verdict on the CURRENT allocation: None = not yet reviewed,
    # True = approved, False = needs revision. The Strategist resets this to None
    # whenever it writes a new allocation, so every allocation gets re-reviewed.
    critic_approved: bool

    # Set True by the Critic when fixing its critique needs NEW external info.
    needs_research: bool
