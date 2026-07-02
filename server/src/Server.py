from dotenv import load_dotenv

from server.src.api.app import create_app


def main():
    # Local dev convenience (v1.2): picks up PRIOTASK_* vars from a .env file
    # in the working directory, if one exists. The Render deploy (wsgi.py)
    # doesn't call main() and sets real env vars instead, so this never runs
    # there - no .env file is ever expected/used in production.
    load_dotenv()
    app = create_app()
    app.run(debug=True)


if __name__ == "__main__":
    main()
