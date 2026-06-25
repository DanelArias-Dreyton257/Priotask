from flask import Flask

from server.src.api.plan_routes import plan_bp
from server.src.api.task_routes import task_bp
from server.src.api.user_routes import user_bp
from server.src.data.db.DB import DB
from server.src.data.db.TaskDAO import TaskDAO
from server.src.data.db.UserDAO import UserDAO
from server.src.services.AuthService import AuthService
from server.src.services.Prioritizer.DailyPlanner import DailyPlanner
from server.src.services.TaskManager import TaskManager
from server.src.services.UserManager import UserManager


def create_app(db_path: str = "priotask.db") -> Flask:
    """
    Wires the persistence layer (Phase 2) and the prioritization layer
    (Phases 1/3) into the Flask app used by the Phase 4 REST API. `db_path`
    can be ":memory:" for tests.
    """
    app = Flask(__name__)

    db = DB(db_path).connect()
    app.user_manager = UserManager(UserDAO(db))
    app.task_manager = TaskManager(TaskDAO(db))
    app.auth_service = AuthService(app.user_manager)
    app.daily_planner = DailyPlanner()

    app.register_blueprint(user_bp, url_prefix="/api")
    app.register_blueprint(task_bp, url_prefix="/api")
    app.register_blueprint(plan_bp, url_prefix="/api")

    return app
