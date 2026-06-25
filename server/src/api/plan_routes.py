from dataclasses import asdict

from flask import Blueprint, current_app, g, jsonify, request

from server.src.api.auth import require_auth
from server.src.services.Prioritizer.DailyPlanner import (
    DEFAULT_AVAILABLE_HOURS_TODAY,
    DEFAULT_PLAN_WEEK_DAYS,
)

plan_bp = Blueprint("plan", __name__)

MAX_PLAN_WEEK_DAYS = 31


def _entry_json(entry):
    return {
        "rank": entry.rank,
        "score": entry.score,
        "recommended_hours_today": entry.recommended_hours_today,
        "task": asdict(current_app.task_manager.to_dto(entry.task)),
    }


@plan_bp.get("/plan/today")
@require_auth
def today_plan():
    try:
        available_hours_today = float(request.args.get("hours", DEFAULT_AVAILABLE_HOURS_TODAY))
    except ValueError:
        return jsonify(error="hours must be a number"), 400

    tasks = current_app.task_manager.get_domain_tasks_for_user(g.user_id)
    entries = current_app.daily_planner.plan(tasks, available_hours_today=available_hours_today)

    return jsonify([_entry_json(entry) for entry in entries])


@plan_bp.get("/plan/week")
@require_auth
def week_plan():
    try:
        available_hours_today = float(request.args.get("hours", DEFAULT_AVAILABLE_HOURS_TODAY))
        days = int(request.args.get("days", DEFAULT_PLAN_WEEK_DAYS))
    except ValueError:
        return jsonify(error="hours must be a number and days must be an integer"), 400

    if not 1 <= days <= MAX_PLAN_WEEK_DAYS:
        return jsonify(error=f"days must be between 1 and {MAX_PLAN_WEEK_DAYS}"), 400

    tasks = current_app.task_manager.get_domain_tasks_for_user(g.user_id)
    day_plans = current_app.daily_planner.plan_week(tasks, days=days, available_hours_today=available_hours_today)

    return jsonify([
        {
            "date": day_plan.date.date().isoformat(),
            "available_hours": day_plan.available_hours,
            "planned_hours_total": sum(entry.recommended_hours_today for entry in day_plan.entries),
            "diagnostics": day_plan.diagnostics,
            "entries": [_entry_json(entry) for entry in day_plan.entries],
            "deadlines": [
                asdict(current_app.task_manager.to_dto(task)) for task in day_plan.deadlines
            ],
        }
        for day_plan in day_plans
    ])
