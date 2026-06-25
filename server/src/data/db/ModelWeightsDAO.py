import sqlite3
from typing import Optional

from server.src.data.db.DB import DB


class ModelWeightsDAO(object):
    def __init__(self, db: Optional[DB] = None):
        self.db = db or DB().connect()

    def upsert(self, user_id: int, model_type: str, payload: bytes, updated_at: str) -> None:
        self.db.execute(
            "INSERT INTO model_weights (user_id, model_type, payload, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, model_type) DO UPDATE SET "
            "payload = excluded.payload, updated_at = excluded.updated_at",
            (user_id, model_type, payload, updated_at),
        )

    def get(self, user_id: int, model_type: str) -> Optional[sqlite3.Row]:
        query = "SELECT * FROM model_weights WHERE user_id = ? AND model_type = ?"
        return self.db.execute(query, (user_id, model_type)).fetchone()

    def delete(self, user_id: int, model_type: str) -> None:
        self.db.execute(
            "DELETE FROM model_weights WHERE user_id = ? AND model_type = ?",
            (user_id, model_type),
        )
