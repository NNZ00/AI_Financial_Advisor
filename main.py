"""Run the FA graph on the example request."""

import uuid

from financial_advisor.graph import build_graph
from financial_advisor.persistence import make_checkpointer
from financial_advisor.request import EXAMPLE_REQUEST


def main():
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
