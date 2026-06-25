from dataclasses import asdict

from flask import Blueprint, current_app, jsonify, request

from server.src.api.auth import require_auth

user_bp = Blueprint("users", __name__)


@user_bp.post("/users")
def register():
    body = request.get_json(silent=True) or {}
    try:
        username, password, email = body["username"], body["password"], body["email"]
    except KeyError as exc:
        return jsonify(error=f"missing field: {exc.args[0]}"), 400

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


@user_bp.post("/auth/logout")
@require_auth
def logout():
    token = request.headers["Authorization"][len("Bearer "):]
    current_app.auth_service.logout(token)
    return "", 204
