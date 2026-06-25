import os

from flask import Flask, render_template

DEFAULT_API_BASE_URL = "http://localhost:5000"


def create_app(api_base_url: str = DEFAULT_API_BASE_URL) -> Flask:
    """
    A static-file server for the Phase 5 web client. All the actual logic
    (auth, tasks, prioritization) lives in the JS modules under
    webapp/static/js/ talking to the server's REST API; this Flask app just
    serves the page and tells the JS where that API lives.
    """
    app = Flask(
        __name__,
        static_folder="webapp/static",
        template_folder="webapp/templates",
    )

    @app.get("/")
    def index():
        return render_template("index.html", api_base_url=api_base_url)

    return app


def main():
    api_base_url = os.environ.get("PRIOTASK_API_BASE_URL", DEFAULT_API_BASE_URL)
    app = create_app(api_base_url)
    app.run(port=5500, debug=True)


if __name__ == "__main__":
    main()
