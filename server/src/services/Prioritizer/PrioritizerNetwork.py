import pickle
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
from tensorflow import keras

from server.src.data.domain.Task import Task
from server.src.services.Prioritizer.FeatureExtractor import FEATURE_ORDER, FeatureExtractor
from server.src.services.Prioritizer.ModelStore import ModelStore, SqliteModelStore
from server.src.services.Prioritizer.PrioritizerModel import PrioritizerModel

HIDDEN_UNITS = 8
TrainingExample = Tuple[Task, datetime, int]

# Bump this string whenever FEATURE_ORDER or HIDDEN_UNITS change so that an
# existing user's stored weights are detected as incompatible and gracefully
# discarded rather than crashing on a shape-mismatch at load time.
_WEIGHTS_FORMAT_VERSION = "v2"


class PrioritizerNetwork(PrioritizerModel):
    """
    Per-user neural network: 3 layers (input, 1 hidden, output), trained on
    which tasks the user actually marks done (PrioritizerTrainer), that
    learns a *correction* on top of FormulaPrioritizer's score v_i rather
    than replacing it outright (see README "The Prioritization Model").

    Phase 12 robustness improvements over the original Phase 6 design:
    - Features are normalized to ~[-1, 1] before reaching the network
      (FeatureExtractor.extract_normalized) so differently-scaled inputs
      don't dominate gradient updates on small per-user datasets.
    - score_many() batches all tasks into a single model.predict() call
      instead of one call per task, so ranking a user's full list costs
      one Keras invocation, not N.
    - Serialized weights carry a format version tag so a future architecture
      change falls back to formula-only scoring for existing users instead
      of crashing on a weight shape-mismatch.
    - fit() uses a train/validation split + EarlyStopping when there's
      enough data (≥10 examples), avoiding overfitting on the tiny dataset.
    - A per-user threading.Lock prevents concurrent train calls from racing
      on ModelStore.save for the same user.
    """

    MODEL_TYPE = "keras_nn_v1"

    def __init__(self, model_store: Optional[ModelStore] = None):
        self.model_store = model_store or SqliteModelStore()
        self.extractor = FeatureExtractor()
        # Each entry is (model, updated_at_str) where updated_at_str matches
        # the value stored in model_weights.updated_at.  _model_for_user
        # re-checks the DB timestamp on every call so a model trained by
        # another worker/process is picked up without a restart.
        self._cache: Dict[int, Tuple[keras.Model, str]] = {}
        self._train_locks: Dict[int, threading.Lock] = {}
        self._lock_registry = threading.Lock()

    def _build_model(self) -> keras.Model:
        model = keras.Sequential([
            keras.layers.Input(shape=(len(FEATURE_ORDER),)),
            keras.layers.Dense(HIDDEN_UNITS, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid"),
        ])
        model.compile(optimizer="adam", loss="binary_crossentropy")
        return model

    def _serialize(self, model: keras.Model) -> bytes:
        data = {
            "version": _WEIGHTS_FORMAT_VERSION,
            "feature_order": FEATURE_ORDER,
            "hidden_units": HIDDEN_UNITS,
            "weights": [w.tolist() for w in model.get_weights()],
        }
        return pickle.dumps(data)

    def _deserialize(self, model: keras.Model, payload: bytes) -> bool:
        """Load weights from payload into model. Returns False if the stored
        format is incompatible with the current architecture (in which case
        the caller should fall back to formula-only scoring)."""
        data = pickle.loads(payload)
        # Legacy format (Phase 6): plain list of weight arrays — treat as
        # compatible so existing users aren't silently reset.
        if isinstance(data, list):
            model.set_weights([np.array(w) for w in data])
            return True
        if (data.get("feature_order") != FEATURE_ORDER
                or data.get("hidden_units") != HIDDEN_UNITS
                or data.get("version") != _WEIGHTS_FORMAT_VERSION):
            return False
        model.set_weights([np.array(w) for w in data["weights"]])
        return True

    def _model_for_user(self, user_id: int) -> Optional[keras.Model]:
        # One cheap timestamp query lets us detect when another process has
        # saved a newer model, without loading the full payload on every call.
        db_updated_at = self.model_store.get_updated_at(user_id, self.MODEL_TYPE)
        cached = self._cache.get(user_id)
        if cached is not None:
            cached_model, cached_updated_at = cached
            if cached_updated_at == db_updated_at:
                return cached_model
            # Another process saved a newer version (or forgot the model); evict.
            del self._cache[user_id]
        if db_updated_at is None:
            return None
        payload = self.model_store.load(user_id, self.MODEL_TYPE)
        if payload is None:
            return None
        model = self._build_model()
        if not self._deserialize(model, payload):
            return None
        self._cache[user_id] = (model, db_updated_at)
        return model

    def _get_train_lock(self, user_id: int) -> threading.Lock:
        with self._lock_registry:
            if user_id not in self._train_locks:
                self._train_locks[user_id] = threading.Lock()
            return self._train_locks[user_id]

    def score(self, task: Task, reference_date: datetime) -> float:
        features = self.extractor.extract(task, reference_date)
        formula_score = features[FEATURE_ORDER.index("formula_score")]

        model = self._model_for_user(task.user_id) if task.user_id is not None else None
        if model is None:
            return formula_score

        norm = self.extractor.normalize(features)
        correction = float(model.predict(np.array([norm]), verbose=0)[0][0])
        return formula_score * (2 * correction)

    def score_many(self, tasks: List[Task], reference_date: datetime):
        """Batch-score all tasks, making at most one model.predict() call per
        distinct user_id that has a trained model. Tasks without a trained
        model fall back to FormulaPrioritizer's score individually."""
        if not tasks:
            return []

        # Separate tasks by user (or no-user) to decide which ones get a
        # batched Keras call vs. a simple formula fallback.
        formula_scores = [
            self.extractor.extract(task, reference_date)[FEATURE_ORDER.index("formula_score")]
            for task in tasks
        ]

        # Group task indices by user_id so we can batch per-user.
        user_groups: Dict[int, List[int]] = {}
        for idx, task in enumerate(tasks):
            if task.user_id is not None:
                user_groups.setdefault(task.user_id, []).append(idx)

        results = list(formula_scores)  # default: formula score for everyone

        for user_id, indices in user_groups.items():
            model = self._model_for_user(user_id)
            if model is None:
                continue
            user_tasks = [tasks[i] for i in indices]
            batch = np.array([
                self.extractor.extract_normalized(t, reference_date) for t in user_tasks
            ])
            corrections = model.predict(batch, verbose=0).flatten()
            for idx, correction in zip(indices, corrections):
                results[idx] = formula_scores[idx] * (2 * float(correction))

        return list(zip(tasks, results))

    def fit(self, user_id: int, examples: List[TrainingExample], epochs: int = 50) -> None:
        """examples: (task, reference_date, label), label=1 for the task the
        user picked to work on, 0 for tasks that were available but weren't."""
        with self._get_train_lock(user_id):
            model = self._model_for_user(user_id) or self._build_model()
            x = np.array([
                self.extractor.extract_normalized(task, ref) for task, ref, _ in examples
            ])
            y = np.array([label for _, _, label in examples], dtype=float)

            # Use a validation split + early stopping once there's enough data
            # to avoid overfitting on the tiny per-user dataset.
            if len(x) >= 10:
                callbacks = [keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True)]
                model.fit(x, y, epochs=epochs, validation_split=0.2,
                          callbacks=callbacks, verbose=0)
            else:
                model.fit(x, y, epochs=epochs, verbose=0)

            saved_at = datetime.now()
            self.model_store.save(user_id, self.MODEL_TYPE, self._serialize(model), saved_at)
            self._cache[user_id] = (model, saved_at.isoformat())

    def forget(self, user_id: int) -> None:
        """Discards a user's trained model, reverting score() to FormulaPrioritizer."""
        self.model_store.delete(user_id, self.MODEL_TYPE)
        self._cache.pop(user_id, None)
