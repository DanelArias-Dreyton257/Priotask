import unittest
from datetime import datetime, timedelta

from server.src.data.domain.Task import Task
from server.src.services.Prioritizer.DailyPlanner import DailyPlanner

REFERENCE = datetime(2026, 1, 1)


def make_task(name="task", days_until_deadline=5.0, hours=8.0, importance=5,
              task_type="", task_subtype="", done=False):
    deadline = REFERENCE + timedelta(days=days_until_deadline)
    return Task(name, deadline, hours, importance, task_type, task_subtype, done=done)


class DailyPlannerTest(unittest.TestCase):

    def setUp(self):
        self.planner = DailyPlanner()

    def test_done_and_zero_effort_tasks_are_excluded(self):
        done_task = make_task("done", done=True)
        zero_effort = make_task("zero", hours=0.0)
        active = make_task("active", hours=1.0)
        plan = self.planner.plan([done_task, zero_effort, active], available_hours_today=6.0,
                                  reference_date=REFERENCE)
        self.assertEqual([entry.task.name for entry in plan], ["active"])

    def test_single_task_gets_full_budget_capped_by_effort(self):
        task = make_task(hours=2.0)
        plan = self.planner.plan([task], available_hours_today=6.0, reference_date=REFERENCE)
        self.assertAlmostEqual(plan[0].recommended_hours_today, 2.0)

    def test_uncapped_tasks_split_budget_proportionally_to_score(self):
        a = make_task("a", days_until_deadline=2.0, hours=24.0, importance=4)
        b = make_task("b", days_until_deadline=10.0, hours=24.0, importance=2)
        plan = self.planner.plan([a, b], available_hours_today=6.0, reference_date=REFERENCE)
        by_name = {entry.task.name: entry for entry in plan}

        total_score = by_name["a"].score + by_name["b"].score
        expected_a = 6.0 * by_name["a"].score / total_score
        expected_b = 6.0 * by_name["b"].score / total_score

        self.assertAlmostEqual(by_name["a"].recommended_hours_today, expected_a)
        self.assertAlmostEqual(by_name["b"].recommended_hours_today, expected_b)
        self.assertAlmostEqual(by_name["a"].recommended_hours_today + by_name["b"].recommended_hours_today, 6.0)

    def test_capped_task_frees_budget_for_the_rest(self):
        small = make_task("small", days_until_deadline=1.0, hours=0.5, importance=10)
        big = make_task("big", days_until_deadline=10.0, hours=24.0, importance=1)
        plan = self.planner.plan([small, big], available_hours_today=6.0, reference_date=REFERENCE)
        by_name = {entry.task.name: entry for entry in plan}

        self.assertAlmostEqual(by_name["small"].recommended_hours_today, 0.5)
        self.assertAlmostEqual(by_name["big"].recommended_hours_today, 5.5)

    def test_overdue_tasks_are_never_starved_by_current_tasks(self):
        overdue = make_task("overdue", days_until_deadline=-3.0, hours=1.0, importance=1)
        many_current = [
            make_task(f"current{i}", days_until_deadline=20.0, hours=24.0, importance=10)
            for i in range(20)
        ]
        plan = self.planner.plan([overdue] + many_current, available_hours_today=1.0, reference_date=REFERENCE)
        by_name = {entry.task.name: entry for entry in plan}

        self.assertAlmostEqual(by_name["overdue"].recommended_hours_today, 1.0)
        for i in range(20):
            self.assertAlmostEqual(by_name[f"current{i}"].recommended_hours_today, 0.0)

    def test_rank_follows_score_order(self):
        urgent = make_task("urgent", days_until_deadline=0.5, hours=10.0, importance=8)
        relaxed = make_task("relaxed", days_until_deadline=20.0, hours=1.0, importance=1)
        plan = self.planner.plan([relaxed, urgent], available_hours_today=6.0, reference_date=REFERENCE)
        self.assertEqual([(entry.rank, entry.task.name) for entry in plan], [(1, "urgent"), (2, "relaxed")])

    def test_empty_task_list_returns_empty_plan(self):
        self.assertEqual(self.planner.plan([], reference_date=REFERENCE), [])

    def test_zero_budget_gives_no_hours(self):
        task = make_task(hours=2.0)
        plan = self.planner.plan([task], available_hours_today=0.0, reference_date=REFERENCE)
        self.assertAlmostEqual(plan[0].recommended_hours_today, 0.0)

    def test_plan_week_returns_one_day_plan_per_day(self):
        task = make_task(hours=1.0)
        week = self.planner.plan_week([task], days=7, available_hours_today=6.0, reference_date=REFERENCE)
        self.assertEqual(len(week), 7)
        self.assertEqual([day.date for day in week], [REFERENCE + timedelta(days=i) for i in range(7)])

    def test_plan_week_carries_remaining_effort_forward(self):
        task = make_task(hours=10.0, days_until_deadline=20.0)
        week = self.planner.plan_week([task], days=3, available_hours_today=4.0, reference_date=REFERENCE)

        self.assertAlmostEqual(week[0].entries[0].recommended_hours_today, 4.0)
        self.assertAlmostEqual(week[1].entries[0].recommended_hours_today, 4.0)
        self.assertAlmostEqual(week[2].entries[0].recommended_hours_today, 2.0)

    def test_plan_week_drops_task_once_fully_covered(self):
        task = make_task(hours=4.0, days_until_deadline=20.0)
        week = self.planner.plan_week([task], days=3, available_hours_today=6.0, reference_date=REFERENCE)

        self.assertAlmostEqual(week[0].entries[0].recommended_hours_today, 4.0)
        self.assertEqual(week[1].entries, [])
        self.assertEqual(week[2].entries, [])

    def test_plan_week_does_not_mutate_input_tasks(self):
        task = make_task(hours=4.0, days_until_deadline=20.0)
        self.planner.plan_week([task], days=3, available_hours_today=6.0, reference_date=REFERENCE)
        self.assertAlmostEqual(task.expected_duration_h, 4.0)
        self.assertFalse(task.done)

    def test_plan_week_flags_deadlines_on_their_due_day_even_without_hours(self):
        due_soon = make_task("due-soon", days_until_deadline=2.0, hours=1.0, importance=1)
        hungry = make_task("hungry", days_until_deadline=20.0, hours=24.0, importance=10)
        week = self.planner.plan_week(
            [due_soon, hungry], days=4, available_hours_today=0.0, reference_date=REFERENCE,
        )
        self.assertEqual([task.name for task in week[2].deadlines], ["due-soon"])
        self.assertEqual(week[2].deadlines[0].expected_duration_h, 1.0)

    def test_plan_week_excludes_already_done_tasks(self):
        done_task = make_task("done", done=True)
        week = self.planner.plan_week([done_task], days=2, reference_date=REFERENCE)
        self.assertEqual(week[0].entries, [])
        self.assertEqual(week[0].deadlines, [])


if __name__ == "__main__":
    unittest.main()
