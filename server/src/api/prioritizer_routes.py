from flask import Blueprint, current_app, g, jsonify

from server.src.api.auth import require_auth
from server.src.services.Prioritizer.PrioritizerNetwork import PrioritizerNetwork

prioritizer_bp = Blueprint("prioritizer", __name__)


@prioritizer_bp.post("/prioritizer/train")
@require_auth
def train():
    trained = current_app.prioritizer_trainer.train(g.user_id)
    return jsonify(trained=trained)


@prioritizer_bp.get("/prioritizer/status")
@require_auth
def status():
    """Side-effect-free check: is there a trained model for this user, and when
    was it last updated - doesn't itself trigger training."""
    row = current_app.model_weights_dao.get(g.user_id, PrioritizerNetwork.MODEL_TYPE)
    return jsonify(trained=row is not None, updated_at=row["updated_at"] if row else None)


@prioritizer_bp.delete("/prioritizer/model")
@require_auth
def delete_model():
    """Discards the user's trained model, reverting to formula-only scoring."""
    current_app.prioritizer_network.forget(g.user_id)
    return jsonify(trained=False)
