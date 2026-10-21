"""Build a small synthetic 'sprint' repository with labelled ground truth.

Used by the evaluation script, the tests and the README demo so that results are
reproducible without network access.   python scripts/make_demo_repo.py demo_repo
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

# (subject, body, gold_category, is_noise, file)
COMMITS = [
    ("feat(auth): add OAuth login with Google", "Users previously had to create a password for every deployment. OAuth removes that step so that onboarding takes seconds.\n\nCloses #12", "feature", False, "src/auth/oauth.py"),
    ("fix(api): handle empty payload in /orders", "The endpoint crashed with a 500 because the JSON body was None. We now return a 400 with a helpful message.\n\nFixes #31", "fix", False, "src/api/orders.py"),
    ("perf(db): add index on orders.created_at", "Dashboard queries were scanning the whole table which caused 4s page loads. The index brings this under 200ms.", "perf", False, "src/db/schema.sql"),
    ("docs: describe environment variables in README", "", "docs", False, "README.md"),
    ("refactor(core): split billing module into smaller files", "This makes it easier to test each calculation in isolation.", "refactor", False, "src/core/billing.py"),
    ("test(api): cover pagination edge cases", "", "test", False, "tests/test_pagination.py"),
    ("chore(deps): bump requests to 2.32", "", "build", False, "requirements.txt"),
    ("feat(export)!: change CSV export columns to snake_case", "BREAKING CHANGE: Column headers are now snake_case, so existing import scripts must be updated.\n\nCloses #40", "breaking", False, "src/export/csv.py"),
    ("ci: run tests on Python 3.11 and 3.12", "", "build", False, ".github/workflows/ci.yml"),
    ("fix(ui): button text overflowed on mobile screens", "Long translations were clipped because the label had a fixed width.", "fix", False, "src/ui/button.css"),
    ("Add dark mode toggle to settings page", "Several users asked for it because the bright UI was hard to read at night. Preference is stored per account.", "feature", False, "src/ui/settings.js"),
    ("Fixes crash when uploading a file with unicode name", "The upload handler used ascii encoding which caused a UnicodeEncodeError. Switched to utf-8.\n\nFixes #55", "fix", False, "src/upload/handler.py"),
    ("Speed up search by caching tokenised documents", "Search was re-tokenising every document on each request. Caching reduces response time from 900ms to 120ms.", "perf", False, "src/search/index.py"),
    ("Update documentation for the webhook API", "", "docs", False, "docs/webhooks.md"),
    ("Add unit tests for the invoice calculator", "", "test", False, "tests/test_invoice.py"),
    ("Rename UserManager to AccountService", "The old name was confusing since it also handles organisations.", "refactor", False, "src/core/accounts.py"),
    ("Upgrade Docker base image to python:3.12-slim", "", "build", False, "Dockerfile"),
    ("Implement rate limiting for public API", "Without limits a single client could exhaust the worker pool, which caused outages last sprint.", "feature", False, "src/api/limits.py"),
    ("Resolve race condition in session cleanup job", "Two workers could delete the same session because there was no lock. Added a row-level lock.", "fix", False, "src/jobs/cleanup.py"),
    ("Introduce retry with backoff for email sending", "Transient SMTP errors used to drop notifications silently.", "feature", False, "src/notify/email.py"),
    ("Make login page not explode on empty password", "It threw a TypeError so users saw a blank screen. Now shows a validation message.", "fix", False, "src/auth/login.py"),
    ("Users can now pin projects to the sidebar", "Teams with many projects wanted quick access to the ones they use daily.", "feature", False, "src/ui/sidebar.js"),
    ("Clean up unused imports across the codebase", "", "refactor", False, "src/core/utils.py"),
    ("Drop support for Python 3.8", "Python 3.8 is end-of-life and blocks newer dependencies.\n\nBREAKING CHANGE: Python 3.9 or newer is now required.", "breaking", False, "setup.cfg"),
    ("Correct totals when discount exceeds item price", "Negative totals were shown to customers because the discount was not clamped.", "fix", False, "src/core/pricing.py"),
    ("Show upload progress bar", "Large uploads looked frozen so users retried and created duplicates.", "feature", False, "src/ui/upload.js"),
    ("Reduce memory usage of report generator", "Reports with 100k rows exhausted memory because everything was loaded at once. Rows are now streamed.", "perf", False, "src/reports/gen.py"),
    ("Improve error messages", "", "feature", False, "src/core/errors.py"),
    ("Tidy API client", "", "refactor", False, "src/client/api.py"),
    ("Move config loading into its own module", "Keeps settings parsing separate from business logic.", "refactor", False, "src/core/config.py"),
    ("Merge branch 'main' into feature/oauth", "", "chore", True, "src/auth/oauth.py"),
    ("WIP", "", "chore", True, "src/tmp.py"),
    ("wip: trying something", "", "chore", True, "src/tmp.py"),
    ("fixup! add OAuth login", "", "chore", True, "src/auth/oauth.py"),
    ("Merge pull request #61 from team/search-cache", "", "chore", True, "src/search/index.py"),
    ("typo", "", "chore", True, "README.md"),
    ("minor", "", "chore", True, "src/core/utils.py"),
    ("Bump version to 2.4.0", "", "chore", True, "setup.cfg"),
    ("formatting", "", "chore", True, "src/core/utils.py"),
    ("Merge branch 'main' of github.com:team/app", "", "chore", True, "src/core/utils.py"),
]


def build(path: str, days: int = 13) -> str:
    os.makedirs(path, exist_ok=True)
    run = lambda *a, env=None: subprocess.run(["git", "-C", path, *a], check=True, capture_output=True,
                                              env={**os.environ, **(env or {})})
    run("init", "-q", "-b", "main")
    run("config", "user.email", "dev@example.com")
    run("config", "user.name", "Demo Dev")
    start = datetime.now(timezone.utc) - timedelta(days=days)
    step = timedelta(days=days) / len(COMMITS)
    truth = []
    for i, (subject, body, cat, noise, f) in enumerate(COMMITS):
        full = os.path.join(path, f)
        os.makedirs(os.path.dirname(full) or path, exist_ok=True)
        with open(full, "a", encoding="utf-8") as fh:
            fh.write(f"# change {i}\n")
        run("add", "-A")
        when = (start + step * i).strftime("%Y-%m-%dT%H:%M:%S%z")
        msg = subject + ("\n\n" + body if body else "")
        run("commit", "-q", "-m", msg, env={"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when})
        sha = subprocess.run(["git", "-C", path, "rev-parse", "--short=7", "HEAD"], capture_output=True,
                             text=True).stdout.strip()
        truth.append({"id": sha, "subject": subject, "gold_category": cat, "gold_noise": noise,
                      "gold_has_reason": bool(body.strip()) and not noise})
    with open(os.path.join(path, ".gold.json"), "w") as fh:
        json.dump(truth, fh, indent=1)
    return path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "demo_repo"
    build(out)
    print(f"built {out} with {len(COMMITS)} commits")
