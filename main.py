"""Entry point: run the trading-agent graph on the example request.

STAGE 5: each run is checkpointed to SQLite, keyed by a thread_id, so the full
state is persisted durably and can be inspected or resumed later (inspect_run.py).
"""
import uuid

from financial_advisor.graph import build_graph
from financial_advisor.persistence import make_checkpointer
from financial_advisor.request import EXAMPLE_REQUEST


def main():
    # A fresh thread_id = a new, independent analysis. Reusing an existing
    # thread_id would RESUME that run from its last checkpoint instead.
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    checkpointer = make_checkpointer()
    try:
        graph = build_graph(checkpointer=checkpointer)
        result = graph.invoke(
            {"user_request": EXAMPLE_REQUEST, "messages": []},
            config=config,
        )
    finally:
        checkpointer.conn.close()

    print("=== Message trace (order the agents ran) ===")
    for m in result["messages"]:
        print(f"  - {m.content}")

    print("\n=== Final proposal ===")
    print(result.get("final_proposal", "(none)"))

    print("\n=== Persistence ===")
    print(f"thread_id: {thread_id}")
    print(f"inspect this run in a fresh process with:")
    print(f"    python inspect_run.py {thread_id}")


if __name__ == "__main__":
    main()