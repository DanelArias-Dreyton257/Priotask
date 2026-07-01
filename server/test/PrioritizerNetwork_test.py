import pickle
import threading
import unittest
from datetime import datetime, timedelta

from server.src.data.db.CompletionSnapshotDAO import CompletionSnapshotDAO
from server.src.data.db.DB import DB
from server.src.data.db.ModelWeightsDAO import ModelWeightsDAO
from server.src.data.db.TaskDAO import TaskDAO
from server.src.data.db.UserDAO import UserDAO
from server.src.data.domain.Task import Task
from server.src.services.Prioritizer.FeatureExtractor import FEATURE_ORDER, FeatureExtractor
from server.src.services.Prioritizer.FormulaPrioritizer import FormulaPrioritizer
from server.src.services.Prioritizer.ModelStore import SqliteModelStore
from server.src.services.Prioritizer.PrioritizerNetwork import HIDDEN_UNITS, PrioritizerNetwork, _WEIGHTS_FORMAT_VERSION
from server.src.services.Prioritizer.PrioritizerTrainer import PrioritizerTrainer
from server.src.services.TaskManager import TaskManager
from server.src.services.UserManager import UserManager

REFERENCE = datetime(2026, 1, 1)


def make_task(name="task", days_until_deadline=5.0, hours=8.0, importance=5, user_id=None):
    deadline = REFERENCE + timedelta(days=days_until_deadline)
    return Task(name, deadline, hours, importance, task_id=None, user_id=user_id)


class FeatureExtractorTest(unittest.TestCase):

    def test_extract_matches_formula_building_blocks(self):
        task = make_task(hours=24.0, days_until_deadline=2.0, importance=4)
        extractor = FeatureExtractor()
        formula = FormulaPrioritizer()

        features = extractor.extract(task, REFERENCE)

        self.assertEqual(len(features), len(FEATURE_ORDER))
        self.assertAlmostEqual(features[FEATURE_ORDER.index("effort_days")], formula.effort_days(task))
        self.assertAlmostEqual(
            features[FEATURE_ORDER.index("days_remaining")], formula.days_remaining(task, REFERENCE),
        )
        self.assertAlmostEqual(features[FEATURE_ORDER.index("importance")], float(task.importance))
        self.assertAlmostEqual(features[FEATURE_ORDER.index("urgency")], formula.urgency(task, REFERENCE))
        self.assertAlmostEqual(features[FEATURE_ORDER.index("formula_score")], formula.score(task, REFERENCE))


class ModelStoreTest(unittest.TestCase):

    def setUp(self):
        self.db = DB(":memory:").connect()
        users = UserManager(UserDAO(self.db))
        self.user_id = users.create_user("alice", "s3cret", "alice@example.com").user_id
        self.store = SqliteModelStore(ModelWeightsDAO(self.db))

    def tearDown(self):
        self.db.close()

    def test_load_missing_model_returns_none(self):
        self.assertIsNone(self.store.load(self.user_id, "keras_nn_v1"))

    def test_save_then_load_round_trips_payload(self):
        self.store.save(self.user_id, "keras_nn_v1", b"weights-bytes", datetime.now())
        self.assertEqual(self.store.load(self.user_id, "keras_nn_v1"), b"weights-bytes")

    def test_save_twice_overwrites_payload(self):
        self.store.save(self.user_id, "keras_nn_v1", b"first", datetime.now())
        self.store.save(self.user_id, "keras_nn_v1", b"second", datetime.now())
        self.assertEqual(self.store.load(self.user_id, "keras_nn_v1"), b"second")

    def test_delete_removes_payload(self):
        self.store.save(self.user_id, "keras_nn_v1", b"weights-bytes", datetime.now())
        self.store.delete(self.user_id, "keras_nn_v1")
        self.assertIsNone(self.store.load(self.user_id, "keras_nn_v1"))


class PrioritizerNetworkTest(unittest.TestCase):

    def setUp(self):
        self.db = DB(":memory:").connect()
        users = UserManager(UserDAO(self.db))
        self.user_id = users.create_user("alice", "s3cret", "alice@example.com").user_id
        self.store = SqliteModelStore(ModelWeightsDAO(self.db))

    def tearDown(self):
        self.db.close()

    def test_score_falls_back_to_formula_score_when_untrained(self):
        network = PrioritizerNetwork(self.store)
        task = make_task(user_id=self.user_id)
        self.assertAlmostEqual(network.score(task, REFERENCE), FormulaPrioritizer().score(task, REFERENCE))

    def test_score_falls_back_to_formula_score_without_user_id(self):
        network = PrioritizerNetwork(self.store)
        task = make_task(user_id=None)
        self.assertAlmostEqual(network.score(task, REFERENCE), FormulaPrioritizer().score(task, REFERENCE))

    def test_fit_persists_weights_usable_by_a_fresh_instance(self):
        chosen = make_task("chosen", days_until_deadline=1.0, importance=8, user_id=self.user_id)
        skipped = make_task("skipped", days_until_deadline=20.0, importance=1, user_id=self.user_id)
        examples = [(chosen, REFERENCE, 1), (skipped, REFERENCE, 0)]

        trainer_network = PrioritizerNetwork(self.store)
        trainer_network.fit(self.user_id, examples, epochs=5)

        fresh_network = PrioritizerNetwork(self.store)
        # Just needs to run end-to-end against the persisted weights, not a
        # specific value (the small/random dataset can't pin one down).
        score = fresh_network.score(chosen, REFERENCE)
        self.assertIsInstance(score, float)

    def test_forget_deletes_weights_and_clears_cache(self):
        chosen = make_task("chosen", days_until_deadline=1.0, importance=8, user_id=self.user_id)
        skipped = make_task("skipped", days_until_deadline=20.0, importance=1, user_id=self.user_id)
        network = PrioritizerNetwork(self.store)
        network.fit(self.user_id, [(chosen, REFERENCE, 1), (skipped, REFERENCE, 0)], epochs=5)

        network.forget(self.user_id)

        self.assertIsNone(self.store.load(self.user_id, PrioritizerNetwork.MODEL_TYPE))
        self.assertAlmostEqual(network.score(chosen, REFERENCE), FormulaPrioritizer().score(chosen, REFERENCE))


class PrioritizerTrainerTest(unittest.TestCase):

    def setUp(self):
        self.db = DB(":memory:").connect()
        self.task_manager = TaskManager(TaskDAO(self.db), CompletionSnapshotDAO(self.db))
        users = UserManager(UserDAO(self.db))
        self.user_id = users.create_user("alice", "s3cret", "alice@example.com").user_id
        self.store = SqliteModelStore(ModelWeightsDAO(self.db))
        self.network = PrioritizerNetwork(self.store)
        self.trainer = PrioritizerTrainer(self.task_manager, self.network)

    def tearDown(self):
        self.db.close()

    def test_train_is_a_noop_without_enough_signal(self):
        self.task_manager.create_task(
            user_id=self.user_id, name="only one", deadline=REFERENCE, expected_duration_h=1.0, importance=1,
        )
        self.assertFalse(self.trainer.train(self.user_id))
        self.assertIsNone(self.store.load(self.user_id, PrioritizerNetwork.MODEL_TYPE))

    def test_train_fits_and_persists_once_both_labels_are_present(self):
        for i in range(3):
            done = self.task_manager.create_task(
                user_id=self.user_id, name=f"done-{i}", deadline=REFERENCE,
                expected_duration_h=1.0, importance=5,
            )
            self.task_manager.mark_done(done.task_id, REFERENCE)
        self.task_manager.create_task(
            user_id=self.user_id, name="open", deadline=REFERENCE + timedelta(days=10),
            expected_duration_h=1.0, importance=1,
        )

        self.assertTrue(self.trainer.train(self.user_id))
        self.assertIsNotNone(self.store.load(self.user_id, PrioritizerNetwork.MODEL_TYPE))

    def test_build_examples_uses_completion_snapshot_for_accurate_negatives(self):
        a = self.task_manager.create_task(
            user_id=self.user_id, name="a", deadline=REFERENCE, expected_duration_h=1.0, importance=5,
        )
        self.task_manager.create_task(
            user_id=self.user_id, name="b", deadline=REFERENCE, expected_duration_h=1.0, importance=1,
        )
        self.task_manager.mark_done(a.task_id, REFERENCE)
        # Created only after a's completion: must not be treated as a negative for a's snapshot.
        self.task_manager.create_task(
            user_id=self.user_id, name="c", deadline=REFERENCE, expected_duration_h=1.0, importance=1,
        )

        examples = self.trainer._build_examples(self.user_id)
        snapshot_examples = {(task.name, reference_date, label) for task, reference_date, label in examples
                              if reference_date == REFERENCE}
        current_negatives = {task.name for task, reference_date, label in examples
                              if label == 0 and reference_date != REFERENCE}

        self.assertIn(("a", REFERENCE, 1), snapshot_examples)
        self.assertIn(("b", REFERENCE, 0), snapshot_examples)
        self.assertNotIn(("c", REFERENCE, 0), snapshot_examples)
        # c is still open "now" though, so it's still valid signal via the current-open fallback.
        self.assertIn("c", current_negatives)


class FeatureExtractorNormalizationTest(unittest.TestCase):

    def test_normalized_features_are_bounded(self):
        extractor = FeatureExtractor()
        task = make_task(hours=8.0, days_until_deadline=7.0, importance=5)
        normalized = extractor.extract_normalized(task, REFERENCE)
        self.assertEqual(len(normalized), len(FEATURE_ORDER))
        for value in normalized:
            self.assertGreaterEqual(value, -1.5, "normalized feature should not be far below -1")
            self.assertLessEqual(value, 3.5, "normalized feature should not be far above 1")

    def test_importance_normalized_to_zero_one(self):
        extractor = FeatureExtractor()
        for importance in (1, 5, 10):
            task = make_task(importance=importance, days_until_deadline=10.0)
            norm = extractor.extract_normalized(task, REFERENCE)
            importance_idx = FEATURE_ORDER.index("importance")
            self.assertAlmostEqual(norm[importance_idx], importance / 10.0)

    def test_overdue_task_days_remaining_normalizes_negative(self):
        extractor = FeatureExtractor()
        task = make_task(days_until_deadline=-5.0)
        norm = extractor.extract_normalized(task, REFERENCE)
        days_idx = FEATURE_ORDER.index("days_remaining")
        self.assertLess(norm[days_idx], 0.0)

    def test_normalize_is_consistent_with_extract(self):
        extractor = FeatureExtractor()
        task = make_task()
        raw = extractor.extract(task, REFERENCE)
        self.assertEqual(extractor.normalize(raw), extractor.extract_normalized(task, REFERENCE))


class PrioritizerNetworkWeightVersioningTest(unittest.TestCase):

    def setUp(self):
        self.db = DB(":memory:").connect()
        users = UserManager(UserDAO(self.db))
        self.user_id = users.create_user("alice", "s3cret", "alice@example.com").user_id
        self.store = SqliteModelStore(ModelWeightsDAO(self.db))

    def tearDown(self):
        self.db.close()

    def test_incompatible_feature_order_falls_back_to_formula(self):
        stale_payload = pickle.dumps({
            "version": _WEIGHTS_FORMAT_VERSION,
            "feature_order": ["wrong_feature"],
            "hidden_units": HIDDEN_UNITS,
            "weights": [],
        })
        self.store.save(self.user_id, PrioritizerNetwork.MODEL_TYPE, stale_payload, datetime.now())

        network = PrioritizerNetwork(self.store)
        task = make_task(user_id=self.user_id)
        self.assertAlmostEqual(
            network.score(task, REFERENCE),
            FormulaPrioritizer().score(task, REFERENCE),
        )

    def test_incompatible_hidden_units_falls_back_to_formula(self):
        stale_payload = pickle.dumps({
            "version": _WEIGHTS_FORMAT_VERSION,
            "feature_order": FEATURE_ORDER,
            "hidden_units": 999,
            "weights": [],
        })
        self.store.save(self.user_id, PrioritizerNetwork.MODEL_TYPE, stale_payload, datetime.now())

        network = PrioritizerNetwork(self.store)
        task = make_task(user_id=self.user_id)
        self.assertAlmostEqual(
            network.score(task, REFERENCE),
            FormulaPrioritizer().score(task, REFERENCE),
        )

    def test_legacy_format_list_still_loads(self):
        chosen = make_task("chosen", days_until_deadline=1.0, importance=8, user_id=self.user_id)
        skipped = make_task("skipped", days_until_deadline=20.0, importance=1, user_id=self.user_id)

        trainer = PrioritizerNetwork(self.store)
        trainer.fit(self.user_id, [(chosen, REFERENCE, 1), (skipped, REFERENCE, 0)], epochs=3)

        # Overwrite with legacy payload (plain list of weight arrays).
        trained_model = trainer._model_for_user(self.user_id)
        legacy_payload = pickle.dumps([w.tolist() for w in trained_model.get_weights()])
        self.store.save(self.user_id, PrioritizerNetwork.MODEL_TYPE, legacy_payload, datetime.now())

        fresh = PrioritizerNetwork(self.store)
        score = fresh.score(chosen, REFERENCE)
        self.assertIsInstance(score, float)


class PrioritizerNetworkScoreManyTest(unittest.TestCase):

    def setUp(self):
        self.db = DB(":memory:").connect()
        users = UserManager(UserDAO(self.db))
        self.user_id = users.create_user("alice", "s3cret", "alice@example.com").user_id
        self.store = SqliteModelStore(ModelWeightsDAO(self.db))

    def tearDown(self):
        self.db.close()

    def test_score_many_matches_score_per_task_when_untrained(self):
        network = PrioritizerNetwork(self.store)
        tasks = [
            make_task("a", days_until_deadline=3.0, importance=8, user_id=self.user_id),
            make_task("b", days_until_deadline=10.0, importance=2, user_id=self.user_id),
        ]
        batch_results = dict(network.score_many(tasks, REFERENCE))
        for task in tasks:
            self.assertAlmostEqual(batch_results[task], network.score(task, REFERENCE))

    def test_score_many_returns_formula_for_tasks_without_user_id(self):
        network = PrioritizerNetwork(self.store)
        formula = FormulaPrioritizer()
        tasks = [
            make_task("x", user_id=None),
            make_task("y", user_id=None),
        ]
        for task, score in network.score_many(tasks, REFERENCE):
            self.assertAlmostEqual(score, formula.score(task, REFERENCE))

    def test_score_many_empty_list_returns_empty(self):
        network = PrioritizerNetwork(self.store)
        self.assertEqual(network.score_many([], REFERENCE), [])

    def test_score_many_matches_individual_scores_after_training(self):
        chosen = make_task("chosen", days_until_deadline=1.0, importance=9, user_id=self.user_id)
        skipped = make_task("skipped", days_until_deadline=30.0, importance=1, user_id=self.user_id)
        network = PrioritizerNetwork(self.store)
        network.fit(self.user_id, [(chosen, REFERENCE, 1), (skipped, REFERENCE, 0)], epochs=3)

        fresh = PrioritizerNetwork(self.store)
        tasks = [chosen, skipped]
        batch = dict(fresh.score_many(tasks, REFERENCE))
        for task in tasks:
            self.assertAlmostEqual(batch[task], fresh.score(task, REFERENCE), places=5)


class PrioritizerNetworkConcurrencyTest(unittest.TestCase):

    def setUp(self):
        self.db = DB(":memory:").connect()
        users = UserManager(UserDAO(self.db))
        self.user_id = users.create_user("alice", "s3cret", "alice@example.com").user_id
        self.store = SqliteModelStore(ModelWeightsDAO(self.db))

    def tearDown(self):
        self.db.close()

    def test_concurrent_train_calls_both_complete_without_exception(self):
        chosen = make_task("chosen", days_until_deadline=1.0, importance=8, user_id=self.user_id)
        skipped = make_task("skipped", days_until_deadline=20.0, importance=1, user_id=self.user_id)
        examples = [(chosen, REFERENCE, 1), (skipped, REFERENCE, 0)]

        network = PrioritizerNetwork(self.store)
        errors = []

        def train():
            try:
                network.fit(self.user_id, examples, epochs=2)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=train) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(errors, [], f"Concurrent training raised: {errors}")
        self.assertIsNotNone(self.store.load(self.user_id, PrioritizerNetwork.MODEL_TYPE))


if __name__ == "__main__":
    unittest.main()
