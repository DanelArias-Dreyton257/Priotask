from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from server.src.data.db.ModelWeightsDAO import ModelWeightsDAO


class ModelStore(ABC):
    """
    Persists opaque, per-user model weights keyed by a `model_type` string.
    Each learning PrioritizerModel owns its own serialization format (e.g.
    PrioritizerNetwork pickles its Keras weight arrays) - this store never
    looks inside `payload`, so a future model (an XGBoost booster, etc.) can
    reuse it under its own `model_type` without any change here.
    """

    @abstractmethod
    def save(self, user_id: int, model_type: str, payload: bytes, updated_at: datetime) -> None:
        raise NotImplementedError

    @abstractmethod
    def load(self, user_id: int, model_type: str) -> Optional[bytes]:
        raise NotImplementedError

    @abstractmethod
    def get_updated_at(self, user_id: int, model_type: str) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, user_id: int, model_type: str) -> None:
        raise NotImplementedError


class SqliteModelStore(ModelStore):
    """Default ModelStore backed by the `model_weights` table (server/src/data/db/DB.py)."""

    def __init__(self, dao: Optional[ModelWeightsDAO] = None):
        self.dao = dao or ModelWeightsDAO()

    def save(self, user_id: int, model_type: str, payload: bytes, updated_at: datetime) -> None:
        self.dao.upsert(user_id, model_type, payload, updated_at.isoformat())

    def load(self, user_id: int, model_type: str) -> Optional[bytes]:
        row = self.dao.get(user_id, model_type)
        return bytes(row["payload"]) if row else None

    def get_updated_at(self, user_id: int, model_type: str) -> Optional[str]:
        return self.dao.get_updated_at(user_id, model_type)

    def delete(self, user_id: int, model_type: str) -> None:
        self.dao.delete(user_id, model_type)
