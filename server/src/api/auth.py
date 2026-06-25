from functools import wraps
from typing import Callable

from flask import current_app, g, jsonify, request


def require_auth(view: Callable) -> Callable:
    """Resolves the `Authorization: Bearer <token>` header into `g.user_id`."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="missing bearer token"), 401

        token = header[len("Bearer "):]
        user_id = current_app.auth_service.resolve_token(token)
        if user_id is None:
            return jsonify(error="invalid or expired token"), 401

        g.user_id = user_id
        return view(*args, **kwargs)

    return wrapped
