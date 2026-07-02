#!/usr/bin/env python
"""
Renders client/src/webapp/templates/index.html into a static dist/ folder
for GitHub Pages. Pages serves this repo as a project site
(https://<user>.github.io/Priotask/), not from the root, so asset paths must
stay relative -- that's why url_for() is stubbed to return a plain relative
path instead of Flask's absolute /static/... one.
"""
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
WEBAPP_DIR = REPO_ROOT / "client" / "src" / "webapp"
DIST_DIR = REPO_ROOT / "dist"


def _url_for(endpoint: str, filename: str = "") -> str:
    if endpoint == "static":
        return f"static/{filename}"
    raise ValueError(f"Unsupported endpoint for static build: {endpoint}")


def build(api_base_url: str, google_client_id: str = "") -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    env = Environment(loader=FileSystemLoader(str(WEBAPP_DIR / "templates")))
    template = env.get_template("index.html")
    html = template.render(api_base_url=api_base_url, google_client_id=google_client_id, url_for=_url_for)
    (DIST_DIR / "index.html").write_text(html, encoding="utf-8")

    shutil.copytree(WEBAPP_DIR / "static", DIST_DIR / "static")


def main():
    # google_client_id (2nd arg) is optional: empty/omitted disables the
    # Sign in with Google button on the built site (v1.1).
    if len(sys.argv) not in (2, 3):
        print("Usage: build_static_site.py <api_base_url> [google_client_id]", file=sys.stderr)
        sys.exit(1)
    api_base_url = sys.argv[1]
    google_client_id = sys.argv[2] if len(sys.argv) == 3 else ""
    build(api_base_url, google_client_id)
    print(f"Built {DIST_DIR} (API base URL: {api_base_url})")


if __name__ == "__main__":
    main()
