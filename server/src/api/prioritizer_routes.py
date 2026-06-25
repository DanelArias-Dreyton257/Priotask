from flask import Blueprint, current_app, g, jsonify

from server.src.api.auth import require_auth

prioritizer_bp = Blueprint("prioritizer", __name__)


@prioritizer_bp.post("/prioritizer/train")
@require_auth
def train():
    trained = current_app.prioritizer_trainer.train(g.user_id)
    return jsonify(trained=trained)
