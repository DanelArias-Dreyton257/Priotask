import pickle
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


class PrioritizerNetwork(PrioritizerModel):
    """
    Per-user neural network: 3 layers (input, 1 hidden, output), trained on
    which tasks the user actually marks done (PrioritizerTrainer), that
    learns a *correction* on top of FormulaPrioritizer's score v_i rather
    than replacing it outright (see README "The Prioritization Model").

    Persistence goes through ModelStore: this class only knows how to turn
    its own weights into bytes and back (`_serialize`/`_deserialize`) under
    its own `MODEL_TYPE`, so a future model (e.g. an XGBoost booster) can
    plug into the same store without touching ModelStore or this class.
    """

    MODEL_TYPE = "keras_nn_v1"

    def __init__(self, model_store: Optional[ModelStore] = None):
        self.model_store = model_store or SqliteModelStore()
        self.extractor = FeatureExtractor()
        self._cache: Dict[int, keras.Model] = {}

    def _build_model(self) -> keras.Model:
        model = keras.Sequential([
            keras.layers.Input(shape=(len(FEATURE_ORDER),)),
            keras.layers.Dense(HIDDEN_UNITS, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid"),
        ])
        model.compile(optimizer="adam", loss="binary_crossentropy")
        return model

    def _serialize(self, model: keras.Model) -> bytes:
        return pickle.dumps([w.tolist() for w in model.get_weights()])

    def _deserialize(self, model: keras.Model, payload: bytes) -> None:
        model.set_weights([np.array(w) for w in pickle.loads(payload)])

    def _model_for_user(self, user_id: int) -> Optional[keras.Model]:
        if user_id in self._cache:
            return self._cache[user_id]
        payload = self.model_store.load(user_id, self.MODEL_TYPE)
        if payload is None:
            return None
        model = self._build_model()
        self._deserialize(model, payload)
        self._cache[user_id] = model
        return model

    def score(self, task: Task, reference_date: datetime) -> float:
        features = self.extractor.extract(task, reference_date)
        formula_score = features[FEATURE_ORDER.index("formula_score")]

        model = self._model_for_user(task.user_id) if task.user_id is not None else None
        if model is None:
            return formula_score

        correction = float(model.predict(np.array([features]), verbose=0)[0][0])
        # correction in [0, 1]; an untrained-but-loaded network starts near
        # 0.5 (sigmoid of ~0 weights), so the *2 multiplier starts near 1 -
        # i.e. it never silently zeroes out the formula score before training.
        return formula_score * (2 * correction)

    def fit(self, user_id: int, examples: List[TrainingExample], epochs: int = 50) -> None:
        """examples: (task, reference_date, label), label=1 for the task the
        user picked to work on, 0 for tasks that were available but weren't."""
        model = self._model_for_user(user_id) or self._build_model()
        x = np.array([self.extractor.extract(task, reference_date) for task, reference_date, _ in examples])
        y = np.array([label for _, _, label in examples], dtype=float)
        model.fit(x, y, epochs=epochs, verbose=0)

        self._cache[user_id] = model
        self.model_store.save(user_id, self.MODEL_TYPE, self._serialize(model), datetime.now())
