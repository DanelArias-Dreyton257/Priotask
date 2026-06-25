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
from server.src.services.Prioritizer.PrioritizerNetwork import PrioritizerNetwork
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


if __name__ == "__main__":
    unittest.main()
