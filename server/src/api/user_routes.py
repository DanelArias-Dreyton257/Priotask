"""
User endpoints: POST /users (register), POST /auth/login, POST /auth/google
(Google sign-in), POST /auth/logout, GET|PUT /users/me (profile + email
update), POST /users/me/password (change password with current-password
verification), DELETE /users/me (cascade-delete account). Phase 13 adds
/users/me routes; Phase 15 adds DELETE /users/me and server-side input
validation (username ≥ 3 chars, password ≥ 8 chars); v1.1 adds /auth/google.
"""
from dataclasses import asdict

from flask import Blueprint, current_app, g, jsonify, request

from server.src.api.auth import require_auth

user_bp = Blueprint("users", __name__)

_MIN_USERNAME_LEN = 3
_MIN_PASSWORD_LEN = 8


@user_bp.post("/users")
def register():
    body = request.get_json(silent=True) or {}
    try:
        username, password, email = body["username"], body["password"], body["email"]
    except KeyError as exc:
        return jsonify(error=f"missing field: {exc.args[0]}"), 400

    if len(username) < _MIN_USERNAME_LEN:
        return jsonify(error=f"username must be at least {_MIN_USERNAME_LEN} characters"), 400
    if len(password) < _MIN_PASSWORD_LEN:
        return jsonify(error=f"password must be at least {_MIN_PASSWORD_LEN} characters"), 400

    if current_app.user_manager.get_user_by_username(username) is not None:
        return jsonify(error="username already taken"), 409

    user = current_app.user_manager.create_user(username, password, email)
    return jsonify(asdict(user)), 201


@user_bp.post("/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    try:
        username, password = body["username"], body["password"]
    except KeyError as exc:
        return jsonify(error=f"missing field: {exc.args[0]}"), 400

    token = current_app.auth_service.login(username, password)
    if token is None:
        return jsonify(error="invalid username or password"), 401
    return jsonify(token=token)


@user_bp.post("/auth/google")
def login_with_google():
    body = request.get_json(silent=True) or {}
    try:
        id_token_str = body["id_token"]
    except KeyError as exc:
        return jsonify(error=f"missing field: {exc.args[0]}"), 400

    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        return jsonify(error="Google sign-in is not configured"), 503

    result = current_app.auth_service.login_with_google(id_token_str)
    if result is None:
        return jsonify(error="invalid Google credential"), 401
    token, username = result
    return jsonify(token=token, username=username)


@user_bp.post("/auth/logout")
@require_auth
def logout():
    token = request.headers["Authorization"][len("Bearer "):]
    current_app.auth_service.logout(token)
    return "", 204


@user_bp.get("/users/me")
@require_auth
def get_me():
    user = current_app.user_manager.get_user_by_id(g.user_id)
    return jsonify(asdict(user))


@user_bp.put("/users/me")
@require_auth
def update_me():
    body = request.get_json(silent=True) or {}
    try:
        email = body["email"]
    except KeyError as exc:
        return jsonify(error=f"missing field: {exc.args[0]}"), 400

    user = current_app.user_manager.update_email(g.user_id, email)
    return jsonify(asdict(user))


@user_bp.post("/users/me/password")
@require_auth
def change_password():
    body = request.get_json(silent=True) or {}
    try:
        current_password, new_password = body["current_password"], body["new_password"]
    except KeyError as exc:
        return jsonify(error=f"missing field: {exc.args[0]}"), 400

    if len(new_password) < _MIN_PASSWORD_LEN:
        return jsonify(error=f"password must be at least {_MIN_PASSWORD_LEN} characters"), 400

    changed = current_app.user_manager.change_password(g.user_id, current_password, new_password)
    if not changed:
        return jsonify(error="current password is incorrect"), 400
    return "", 204


@user_bp.delete("/users/me")
@require_auth
def delete_account():
    """Cascade-delete: snapshots → model weights → tasks → sessions → user row.
    The token is revoked before the row is gone so it is immediately invalid."""
    user_id = g.user_id
    # Cascade in dependency order so FK constraints are never violated.
    current_app.task_manager.delete_snapshots_for_user(user_id)
    current_app.prioritizer_network.forget(user_id)
    current_app.task_manager.delete_tasks_for_user(user_id)
    current_app.auth_service.revoke_user(user_id)
    current_app.user_manager.delete_user_by_id(user_id)
    return "", 204
