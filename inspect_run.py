"""Read a persisted run back from the checkpoint DB — in a fresh process.

This is the point of Stage 5: a past run's full state (profile, allocation, final
proposal, message trace) outlives the process that produced it. Pass the thread_id
that main.py printed.

    python inspect_run.py <thread_id>
"""
import sys

from financial_advisor.graph import build_graph
from financial_advisor.persistence import make_checkpointer


def main(thread_id: str) -> None:
    config = {"configurable": {"thread_id": thread_id}}

    checkpointer = make_checkpointer()
    try:
        graph = build_graph(checkpointer=checkpointer)
        snapshot = graph.get_state(config)
    finally:
        checkpointer.conn.close()

    if not snapshot.values:
        print(f"No persisted state found for thread_id '{thread_id}'.")
        return

    values = snapshot.values
    print(f"=== Persisted state for thread {thread_id} ===")
    print(f"next step(s) to run: {snapshot.next or '(none — run complete)'}")

    profile = values.get("investor_profile")
    if profile is not None:
        print(f"\n[Profile] {profile}")

    allocation = values.get("proposed_allocation")
    if allocation is not None:
        tickers = ", ".join(f"{h.ticker or h.asset_class} {h.weight_pct:g}%"
                            for h in allocation.holdings)
        print(f"\n[Allocation] {tickers}")

    print("\n[Message trace]")
    for m in values.get("messages", []):
        print(f"  - {m.content}")

    print("\n[Final proposal]")
    print(values.get("final_proposal", "(none)"))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python inspect_run.py <thread_id>")
        sys.exit(1)
    main(sys.argv[1])