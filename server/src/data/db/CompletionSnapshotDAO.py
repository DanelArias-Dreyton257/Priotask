import sqlite3
from typing import List, Optional

from server.src.data.db.DB import DB


class CompletionSnapshotDAO(object):
    """
    Raw access to `completion_snapshots`: one row per task completion,
    recording which other tasks were still open at that moment
    (`open_task_ids`, a JSON-encoded list of task IDs). This is the real
    per-completion "tasks on the table" history PrioritizerTrainer (Phase 6)
    needs, replacing its earlier done-vs-currently-open proxy.
    """

    def __init__(self, db: Optional[DB] = None):
        self.db = db or DB().connect()

    def add_snapshot(self, user_id: int, completed_task_id: int, completed_at: str, open_task_ids: str) -> None:
        self.db.execute(
            "INSERT INTO completion_snapshots (user_id, completed_task_id, completed_at, open_task_ids) "
            "VALUES (?, ?, ?, ?)",
            (user_id, completed_task_id, completed_at, open_task_ids),
        )

    def get_snapshots_for_user(self, user_id: int) -> List[sqlite3.Row]:
        query = "SELECT * FROM completion_snapshots WHERE user_id = ?"
        return self.db.execute(query, (user_id,)).fetchall()

    def count_for_user(self, user_id: int) -> int:
        row = self.db.execute(
            "SELECT COUNT(*) AS n FROM completion_snapshots WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["n"] if row else 0

    def delete_snapshots_for_user(self, user_id: int) -> None:
        self.db.execute("DELETE FROM completion_snapshots WHERE user_id = ?", (user_id,))
