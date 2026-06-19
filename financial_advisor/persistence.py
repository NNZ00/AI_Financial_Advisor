"""Persistence — a SQLite checkpointer wired for our state's custom types.

LangGraph checkpoints the entire graph state at every super-step. Our state holds
custom Pydantic models (InvestorProfile, Allocation, Holding). The serializer will
reconstruct them today, but a future LangGraph version will REFUSE to deserialize
unregistered types unless we declare them safe. We register them once, here, so the
runner (main.py) and the inspector (inspect_run.py) share an identical, future-proof
serializer. Swapping SqliteSaver for PostgresSaver later changes only this file.
"""
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

CHECKPOINT_DB = "financial_advisor.sqlite"

# (module, class) pairs the msgpack deserializer is explicitly allowed to rebuild.
_ALLOWED_TYPES = [
    ("financial_advisor.state", "InvestorProfile"),
    ("financial_advisor.state", "Allocation"),
    ("financial_advisor.state", "Holding"),
]


def make_checkpointer(db_path: str = CHECKPOINT_DB) -> SqliteSaver:
    """Open (or create) the checkpoint DB and return a configured saver.

    The caller owns the connection's lifetime and should close it via
    `checkpointer.conn.close()` when done.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    serde = JsonPlusSerializer(allowed_msgpack_modules=_ALLOWED_TYPES)
    return SqliteSaver(conn, serde=serde)