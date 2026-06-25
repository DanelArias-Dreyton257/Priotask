from dataclasses import asdict
from datetime import datetime

from flask import Blueprint, current_app, g, jsonify, request

from server.src.api.auth import require_auth

task_bp = Blueprint("tasks", __name__)


def _parse_task_fields(body: dict) -> dict:
    return {
        "name": body["name"],
        "deadline": datetime.fromisoformat(body["deadline"]),
        "expected_duration_h": float(body["expected_duration_h"]),
        "importance": int(body["importance"]),
        "task_type": body.get("task_type", ""),
        "task_subtype": body.get("task_subtype", ""),
    }


def _get_owned_task(task_id: int):
    """Returns the TaskDTO if it exists and belongs to g.user_id, else None."""
    task = current_app.task_manager.get_task(task_id)
    if task is None or task.user_id != g.user_id:
        return None
    return task


@task_bp.get("/tasks")
@require_auth
def list_tasks():
    tasks = current_app.task_manager.get_tasks_for_user(g.user_id)
    return jsonify([asdict(task) for task in tasks])


@task_bp.post("/tasks")
@require_auth
def create_task():
    body = request.get_json(silent=True) or {}
    try:
        fields = _parse_task_fields(body)
    except (KeyError, ValueError) as exc:
        return jsonify(error=f"invalid task data: {exc}"), 400

    task = current_app.task_manager.create_task(user_id=g.user_id, **fields)
    return jsonify(asdict(task)), 201


@task_bp.get("/tasks/<int:task_id>")
@require_auth
def get_task(task_id: int):
    task = _get_owned_task(task_id)
    if task is None:
        return jsonify(error="task not found"), 404
    return jsonify(asdict(task))


@task_bp.put("/tasks/<int:task_id>")
@require_auth
def update_task(task_id: int):
    if _get_owned_task(task_id) is None:
        return jsonify(error="task not found"), 404

    body = request.get_json(silent=True) or {}
    try:
        fields = _parse_task_fields(body)
    except (KeyError, ValueError) as exc:
        return jsonify(error=f"invalid task data: {exc}"), 400

    current_app.task_manager.update_task(task_id, **fields)
    return jsonify(asdict(current_app.task_manager.get_task(task_id)))


@task_bp.post("/tasks/<int:task_id>/log-hours")
@require_auth
def log_hours(task_id: int):
    if _get_owned_task(task_id) is None:
        return jsonify(error="task not found"), 404

    body = request.get_json(silent=True) or {}
    try:
        hours = float(body["hours"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="hours must be a number"), 400
    if hours <= 0:
        return jsonify(error="hours must be greater than 0"), 400

    updated = current_app.task_manager.log_hours(task_id, hours)
    return jsonify(asdict(updated))


@task_bp.post("/tasks/<int:task_id>/complete")
@require_auth
def complete_task(task_id: int):
    if _get_owned_task(task_id) is None:
        return jsonify(error="task not found"), 404

    current_app.task_manager.mark_done(task_id)
    return jsonify(asdict(current_app.task_manager.get_task(task_id)))


@task_bp.delete("/tasks/<int:task_id>")
@require_auth
def delete_task(task_id: int):
    if _get_owned_task(task_id) is None:
        return jsonify(error="task not found"), 404

    current_app.task_manager.delete_task(task_id)
    return "", 204
