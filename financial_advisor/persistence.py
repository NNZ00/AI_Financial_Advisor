"""SQLite checkpointer for persistence of runs acreoss sessions."""

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
