"""
Flask application factory (create_app). Wires the DB, DAOs, managers and
services together, registers all API blueprints, and enables CORS for the
browser client on a different origin/port.
"""
import threading

from flask import Flask, request

from server.src.api.plan_routes import plan_bp
from server.src.api.prioritizer_routes import prioritizer_bp
from server.src.api.task_routes import task_bp
from server.src.api.user_routes import user_bp
from server.src.data.db.CompletionSnapshotDAO import CompletionSnapshotDAO
from server.src.data.db.DB import DB
from server.src.data.db.ModelWeightsDAO import ModelWeightsDAO
from server.src.data.db.SessionDAO import SessionDAO
from server.src.data.db.TaskDAO import TaskDAO
from server.src.data.db.UserDAO import UserDAO
from server.src.services.AuthService import AuthService
from server.src.services.Prioritizer.DailyPlanner import DailyPlanner
from server.src.services.Prioritizer.ModelStore import SqliteModelStore
from server.src.services.Prioritizer.PrioritizerNetwork import PrioritizerNetwork
from server.src.services.Prioritizer.PrioritizerService import PrioritizerService
from server.src.services.Prioritizer.PrioritizerTrainer import PrioritizerTrainer
from server.src.services.TaskManager import TaskManager
from server.src.services.UserManager import UserManager


def create_app(db_path: str = "priotask.db") -> Flask:
    """
    Wires the persistence layer (Phase 2) and the prioritization layer
    (Phases 1/3/6) into the Flask app used by the Phase 4 REST API. `db_path`
    can be ":memory:" for tests.
    """
    app = Flask(__name__)

    db = DB(db_path).connect()
    app.user_manager = UserManager(UserDAO(db))
    app.auth_service = AuthService(app.user_manager, SessionDAO(db))

    # PrioritizerNetwork falls back to FormulaPrioritizer's own score until a
    # user has a trained network stored, so wiring it in here is a no-op for
    # everyone until /api/prioritizer/train has run for them (Phase 6).
    app.model_weights_dao = ModelWeightsDAO(db)
    model_store = SqliteModelStore(app.model_weights_dao)
    network = PrioritizerNetwork(model_store)
    app.prioritizer_network = network
    app.daily_planner = DailyPlanner(PrioritizerService(network))

    # Phase 15: auto-retrain callback — fired in a daemon thread by
    # TaskManager.mark_done every AUTO_RETRAIN_EVERY completions.
    trainer = PrioritizerTrainer(None, network)  # task_manager injected below
    app.prioritizer_trainer = trainer

    def _auto_retrain(user_id: int) -> None:
        try:
            trainer.train(user_id)
        except Exception:
            pass

    snapshot_dao = CompletionSnapshotDAO(db)
    task_manager = TaskManager(
        TaskDAO(db), snapshot_dao,
        on_completion=lambda uid: threading.Thread(
            target=_auto_retrain, args=(uid,), daemon=True
        ).start(),
    )
    app.task_manager = task_manager
    trainer.task_manager = task_manager  # complete circular wiring

    app.register_blueprint(user_bp, url_prefix="/api")
    app.register_blueprint(task_bp, url_prefix="/api")
    app.register_blueprint(plan_bp, url_prefix="/api")
    app.register_blueprint(prioritizer_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        # Hit by Render's health check to confirm the deploy is up.
        return {"status": "ok"}, 200

    _enable_cors(app)
    return app


def _enable_cors(app: Flask) -> None:
    """
    The Phase 5 web client is served from its own Flask process (a different
    origin/port), so its fetch() calls need CORS headers. The API has no
    cookies/sessions to protect against CSRF (auth is a bearer token the
    client attaches itself), so allowing any origin is acceptable here.
    """

    @app.before_request
    def _preflight():
        if request.method == "OPTIONS":
            return "", 204

    @app.after_request
    def _add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response
