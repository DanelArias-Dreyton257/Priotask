import unittest
from datetime import datetime, timedelta

from server.src.data.domain.Task import Task
from server.src.services.Prioritizer.FormulaPrioritizer import (
    DEADLINE_OFFSET_DAYS,
    FormulaPrioritizer,
)
from server.src.services.Prioritizer.PrioritizerService import PrioritizerService

REFERENCE = datetime(2026, 1, 1)


def make_task(name="task", days_until_deadline=5.0, hours=8.0, importance=5,
              task_type="", task_subtype=""):
    deadline = REFERENCE + timedelta(days=days_until_deadline)
    return Task(name, deadline, hours, importance, task_type, task_subtype)


class FormulaPrioritizerTest(unittest.TestCase):

    def setUp(self):
        self.model = FormulaPrioritizer()

    def test_effort_days_converts_hours_to_day_fraction(self):
        task = make_task(hours=12.0)
        self.assertAlmostEqual(self.model.effort_days(task), 0.5)

    def test_days_remaining_applies_offset(self):
        task = make_task(days_until_deadline=3.0)
        d = self.model.days_remaining(task, REFERENCE)
        self.assertAlmostEqual(d, 3.0 - DEADLINE_OFFSET_DAYS)

    def test_urgency_current_regime_is_effort_over_days(self):
        task = make_task(days_until_deadline=2.0, hours=24.0)
        d = self.model.days_remaining(task, REFERENCE)
        expected = (24.0 / 24.0) / d
        self.assertAlmostEqual(self.model.urgency(task, REFERENCE), expected)

    def test_urgency_overdue_regime_grows_with_delay(self):
        task = make_task(days_until_deadline=-3.0, hours=24.0)
        d = self.model.days_remaining(task, REFERENCE)
        expected = (2 + abs(d)) * 1.0
        self.assertAlmostEqual(self.model.urgency(task, REFERENCE), expected)

    def test_discontinuity_at_deadline_uses_overdue_branch(self):
        # d_i = 0 exactly: deadline placed offset days after the reference date.
        task = make_task(days_until_deadline=DEADLINE_OFFSET_DAYS, hours=24.0)
        self.assertAlmostEqual(self.model.days_remaining(task, REFERENCE), 0.0)
        self.assertAlmostEqual(self.model.urgency(task, REFERENCE), 2.0)

    def test_score_scales_urgency_by_importance(self):
        task = make_task(days_until_deadline=2.0, hours=24.0, importance=4)
        expected = 4 * self.model.urgency(task, REFERENCE)
        self.assertAlmostEqual(self.model.score(task, REFERENCE), expected)


class PrioritizerServiceTest(unittest.TestCase):

    def setUp(self):
        self.service = PrioritizerService()

    def test_rank_orders_by_score_descending(self):
        urgent = make_task("urgent", days_until_deadline=0.5, hours=10.0, importance=8)
        relaxed = make_task("relaxed", days_until_deadline=20.0, hours=1.0, importance=1)
        ranked = self.service.rank([relaxed, urgent], REFERENCE)
        self.assertEqual([task.name for task, _ in ranked], ["urgent", "relaxed"])

    def test_rank_tie_breaks_lexicographically(self):
        a = make_task("b_name", days_until_deadline=5.0, hours=8.0, importance=5,
                       task_type="x", task_subtype="x")
        b = make_task("a_name", days_until_deadline=5.0, hours=8.0, importance=5,
                       task_type="x", task_subtype="x")
        ranked = self.service.rank([a, b], REFERENCE)
        self.assertEqual([task.name for task, _ in ranked], ["a_name", "b_name"])

    def test_diagnostics_match_manual_computation(self):
        tasks = [
            make_task("a", days_until_deadline=2.0, hours=24.0, importance=4),
            make_task("b", days_until_deadline=10.0, hours=4.0, importance=2),
        ]
        diag = self.service.diagnostics(tasks, REFERENCE)

        model = FormulaPrioritizer()
        values = [model.score(task, REFERENCE) for task in tasks]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)

        self.assertAlmostEqual(diag["mean"], mean)
        self.assertAlmostEqual(diag["std"], variance ** 0.5)
        self.assertAlmostEqual(diag["sum"], sum(values))
        self.assertAlmostEqual(diag["threshold_quarter"], sum(values) / 4)
        self.assertAlmostEqual(diag["threshold_eighth"], sum(values) / 8)

    def test_diagnostics_on_empty_task_list(self):
        diag = self.service.diagnostics([], REFERENCE)
        self.assertEqual(diag["mean"], 0.0)
        self.assertEqual(diag["std"], 0.0)
        self.assertEqual(diag["sum"], 0.0)


if __name__ == "__main__":
    unittest.main()
