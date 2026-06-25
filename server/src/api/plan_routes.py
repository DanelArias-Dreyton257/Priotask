from dataclasses import asdict

from flask import Blueprint, current_app, g, jsonify, request

from server.src.api.auth import require_auth
from server.src.services.Prioritizer.DailyPlanner import DEFAULT_AVAILABLE_HOURS_TODAY

plan_bp = Blueprint("plan", __name__)


@plan_bp.get("/plan/today")
@require_auth
def today_plan():
    try:
        available_hours_today = float(request.args.get("hours", DEFAULT_AVAILABLE_HOURS_TODAY))
    except ValueError:
        return jsonify(error="hours must be a number"), 400

    tasks = current_app.task_manager.get_domain_tasks_for_user(g.user_id)
    entries = current_app.daily_planner.plan(tasks, available_hours_today=available_hours_today)

    return jsonify([
        {
            "rank": entry.rank,
            "score": entry.score,
            "recommended_hours_today": entry.recommended_hours_today,
            "task": asdict(current_app.task_manager.to_dto(entry.task)),
        }
        for entry in entries
    ])
