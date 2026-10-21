"""Flask front-end: enter owner/repo + window, get a rendered changelog preview."""
from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request

from . import pipeline, renderer


def create_app() -> Flask:
    app = Flask(__name__)

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
        except Exception as exc:  # network / API problems should show up as a message, not a 500
            error = f"Could not reach GitHub: {exc}"
        return render_template("index.html", result=result, form=form, error=error,
                               llm=bool(os.environ.get("ANTHROPIC_API_KEY")))

    @app.get("/healthz")
    def health():
        return jsonify(status="ok")

    return app


def _valid_repo(value: str) -> bool:
    import re
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value or ""))


app = create_app()
