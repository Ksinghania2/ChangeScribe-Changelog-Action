"""Flask front-end: enter owner/repo + window, get a rendered changelog preview."""
from __future__ import annotations

import os
import re
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request

from . import pipeline, renderer


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        DEBUG=False,
        TESTING=False,
        MAX_CONTENT_LENGTH=1_048_576,
    )

    @app.get("/")
    def index():
        return render_template("index.html", result=None, form={"repo": "", "since": "14d",
                               "backend": "auto", "release": "Unreleased"}, error=None,
                               llm=bool(os.environ.get("ANTHROPIC_API_KEY")))

    @app.post("/")
    def generate():
        form = {k: request.form.get(k, "").strip() for k in ("repo", "since", "backend", "release")}
        form["since"] = form["since"] or "14d"
        form["release"] = form["release"] or "Unreleased"
        result, error = None, None
        try:
            if not _valid_repo(form["repo"]):
                raise ValueError("Enter a repository as owner/name, e.g. pallets/flask")
            res = pipeline.run(github_repo=form["repo"], since=form["since"],
                               token=os.environ.get("GITHUB_TOKEN"),
                               backend=form["backend"] or "auto", version=form["release"])
            result = {"html": renderer.to_html(res.markdown), "markdown": res.markdown,
                      "backend": res.backend, "raw": res.raw_count, "kept": len(res.entries)}
        except (ValueError, RuntimeError) as exc:
            error = str(exc)
        except Exception as exc:
            error = "The GitHub request failed. Please verify the repository name and try again."
        return render_template("index.html", result=result, form=form, error=error,
                               llm=bool(os.environ.get("ANTHROPIC_API_KEY")))

    @app.get("/healthz")
    def health():
        return jsonify(status="ok")

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; object-src 'none'"
        return response

    return app


def _valid_repo(value: str) -> bool:
    if not value or len(value) > 200:
        return False
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value or "") is None:
        return False
    if value.startswith("http://") or value.startswith("https://"):
        return False
    parsed = urlparse(value)
    return not parsed.scheme and not parsed.netloc and "/" in value


app = create_app()
