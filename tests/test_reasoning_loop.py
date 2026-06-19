"""Force the full reflection + re-grounding cycle, deterministically."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from financial_advisor.graph import build_graph
from financial_advisor.state import InvestorProfile, Allocation, Holding

graph = build_graph()

profile = InvestorProfile(
    capital=5000, currency="EUR", horizon_years=0.33,
    risk_tolerance="low", goals="capital preservation",
    constraints="instant liquidity, no withdrawal penalties",
)

# Deliberately concentrated — the sharpened Critic must reject this.
bad_allocation = Allocation(
    reasoning="Put everything in one money-market ETF for simplicity.",
    holdings=[Holding(
        asset="EUR overnight-rate money market ETF", ticker="XEON",
        asset_class="cash", weight_pct=100.0,
        rationale="A single, very safe instrument.",
    )],
    risk_assessment="Very low volatility; appropriate for a short horizon.",
    suitability_note="Capital preservation only; no growth expected.",
)

# Seed profile + research + the bad allocation so the supervisor routes STRAIGHT to
# the Critic (critic_approved=None means 'not yet reviewed').
seeded_state = {
    "user_request": "Keep 5,000 EUR safe and liquid for 4 months.",
    "messages": [],
    "investor_profile": profile,
    "research_findings": {"summary": "Brief: XEON tracks the EUR overnight rate; a stable money-market ETF."},
    "proposed_allocation": bad_allocation,
    "critic_approved": None,
}

result = graph.invoke(seeded_state)

print("=== Message trace (forced loop test) ===")
for m in result["messages"]:
    print(f"  - {m.content}")
