import os

from server.src.api.app import create_app
from server.src.services.DemoSeeder import seed_demo_data

app = create_app()

if os.environ.get("PRIOTASK_SEED_DEMO") == "true":
    seed_demo_data(app.user_manager, app.task_manager)
