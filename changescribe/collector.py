"""Stage 1 - collect raw history from a local clone or the GitHub REST API."""
from __future__ import annotations

import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import requests

from .models import Change

SEP = "\x1e"   # record separator between commits
FLD = "\x1f"   # field separator inside a commit


def parse_since(value: Optional[str], now: Optional[datetime] = None) -> Optional[datetime]:
    """Accept '14d', '2w', '36h' or an ISO date and return an aware datetime."""
    if not value:
        return None
    now = now or datetime.now(timezone.utc)
    m = re.fullmatch(r"(\d+)\s*([hdw])", value.strip().lower())
    if m:
        n, unit = int(m.group(1)), m.group(2)
        unit_map = {"h": "hours", "d": "days", "w": "weeks"}
        return now - timedelta(**{unit_map[unit]: n})
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def resolve_rev_range(branch: str = "HEAD", since_tag: Optional[str] = None,
                     until_tag: Optional[str] = None) -> str:
    """Translate tag boundaries into a git revision range.

    These are used to generate ranges like `v1.0.0..HEAD` while keeping previous
    branch semantics intact when no tag is supplied.
    """
    if since_tag and until_tag:
        return f"{since_tag}..{until_tag}"
    if since_tag:
        return f"{since_tag}..{branch or 'HEAD'}"
    if until_tag:
        return f"{until_tag}..{branch or 'HEAD'}"
    return branch or "HEAD"


# --------------------------------------------------------------------------- local git
def collect_local(repo_path: str = ".", since: Optional[datetime] = None,
                  until: Optional[datetime] = None, rev_range: str = "HEAD",
                  include_merges: bool = False, since_tag: Optional[str] = None,
                  until_tag: Optional[str] = None) -> List[Change]:
    """Read commits (message + numstat) from a local git repository."""
    fmt = SEP + FLD.join(["%H", "%an", "%aI", "%s", "%b"]) + FLD
    effective_range = rev_range or "HEAD"
    if since_tag or until_tag:
        effective_range = resolve_rev_range(effective_range, since_tag=since_tag, until_tag=until_tag)

    cmd = ["git", "-C", repo_path, "log", effective_range, f"--pretty=format:{fmt}", "--numstat"]
    if not include_merges:
        cmd.append("--no-merges")
    if since:
        cmd.append(f"--since={since.isoformat()}")
    if until:
        cmd.append(f"--until={until.isoformat()}")
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except FileNotFoundError as exc:
        raise RuntimeError("git executable not found") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git log failed: {exc.stderr.strip()}") from exc

    changes: List[Change] = []
    for record in out.split(SEP):
        if not record.strip():
            continue
        parts = record.split(FLD)
        if len(parts) < 6:
            continue
        sha, author, date, subject, body, tail = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        files, adds, dels = [], 0, 0
        for line in tail.strip().splitlines():
            cols = line.split("\t")
            if len(cols) == 3:
                a, d, name = cols
                files.append(name)
                adds += int(a) if a.isdigit() else 0
                dels += int(d) if d.isdigit() else 0
        changes.append(Change(id=sha[:7], title=subject.strip(), body=body.strip(), author=author,
                              date=datetime.fromisoformat(date), files=files,
                              additions=adds, deletions=dels))
    changes.reverse()  # oldest first reads more naturally
    return changes


# --------------------------------------------------------------------------- GitHub
class GitHubClient:
    """Tiny GitHub REST client with pagination, retry and rate-limit handling."""

    def __init__(self, token: Optional[str] = None, api: str = "https://api.github.com",
                 session: Optional[requests.Session] = None):
        self.api = api.rstrip("/")
        self.s = session or requests.Session()
        self.s.headers.update({"Accept": "application/vnd.github+json",
                               "User-Agent": "changescribe"})
        if token:
            self.s.headers["Authorization"] = f"token {token}"

    def get(self, path: str, params: Optional[dict] = None, retries: int = 3):
        url = path if path.startswith("http") else f"{self.api}{path}"
        for attempt in range(retries):
            r = self.s.get(url, params=params, timeout=30)
            if r.status_code in (403, 429) and r.headers.get("X-RateLimit-Remaining") == "0":
                reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 5))
                wait = max(1, min(reset - int(time.time()), 60))
                time.sleep(wait)
                continue
            if r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 404:
                raise RuntimeError(f"GitHub 404 for {url} (check repo name / token scope)")
            r.raise_for_status()
            return r
        raise RuntimeError(f"GitHub request kept failing: {url}")

    def paginate(self, path: str, params: Optional[dict] = None, limit: int = 300):
        params = dict(params or {}, per_page=100)
        url, items = path, []
        while url and len(items) < limit:
            r = self.get(url, params)
            items.extend(r.json())
            url = r.links.get("next", {}).get("url")
            params = None  # the next-url already carries the query string
        return items[:limit]


def collect_github(repo: str, since: Optional[datetime] = None, until: Optional[datetime] = None,
                   token: Optional[str] = None, client: Optional[GitHubClient] = None,
                   branch: Optional[str] = None, max_items: int = 200,
                   dedupe: bool = True) -> List[Change]:
    """Merged PRs (with their discussion) + direct commits not covered by a PR."""
    gh = client or GitHubClient(token)
    base = f"/repos/{repo}"
    params = {"state": "closed", "sort": "updated", "direction": "desc"}
    if branch:
        params["base"] = branch
    prs = gh.paginate(f"{base}/pulls", params, limit=max_items)

    changes: List[Change] = []
    covered = set()
    seen = set()
    for pr in prs:
        merged = pr.get("merged_at")
        if not merged:
            continue
        mdate = datetime.fromisoformat(merged.replace("Z", "+00:00"))
        if (since and mdate < since) or (until and mdate > until):
            continue
        n = pr["number"]
        files = gh.paginate(f"{base}/pulls/{n}/files", limit=300)
        issue_comments = gh.paginate(f"{base}/issues/{n}/comments", limit=50)
        review_comments = gh.paginate(f"{base}/pulls/{n}/comments", limit=50)
        discussion = [c.get("body", "") for c in issue_comments + review_comments
                      if c.get("body") and not (c.get("user") or {}).get("type") == "Bot"]
        if pr.get("merge_commit_sha"):
            covered.add(pr["merge_commit_sha"])
        for c in gh.paginate(f"{base}/pulls/{n}/commits", limit=100):
            covered.add(c["sha"])
        change = Change(
            id=f"PR#{n}", title=pr["title"], body=pr.get("body") or "",
            author=(pr.get("user") or {}).get("login", ""), date=mdate,
            files=[f["filename"] for f in files],
            additions=sum(f.get("additions", 0) for f in files),
            deletions=sum(f.get("deletions", 0) for f in files),
            discussion=discussion, labels=[l["name"] for l in pr.get("labels", [])],
            pr_number=n, url=pr.get("html_url", ""))
        if dedupe and change.id in seen:
            continue
        seen.add(change.id)
        changes.append(change)

    cparams = {}
    if since:
        cparams["since"] = since.isoformat()
    if until:
        cparams["until"] = until.isoformat()
    if branch:
        cparams["sha"] = branch
    for c in gh.paginate(f"{base}/commits", cparams, limit=max_items):
        sha = c["sha"]
        if sha in covered or len(c.get("parents", [])) > 1:
            continue
        msg = c["commit"]["message"]
        subject, _, body = msg.partition("\n")
        detail = gh.get(f"{base}/commits/{sha}").json()
        files = detail.get("files", [])
        ch = Change(
            id=sha[:7], title=subject.strip(), body=body.strip(),
            author=(c.get("author") or {}).get("login") or c["commit"]["author"]["name"],
            date=datetime.fromisoformat(c["commit"]["author"]["date"].replace("Z", "+00:00")),
            files=[f["filename"] for f in files],
            additions=sum(f.get("additions", 0) for f in files),
            deletions=sum(f.get("deletions", 0) for f in files),
            url=c.get("html_url", ""))
        if dedupe and ch.id in seen:
            continue
        seen.add(ch.id)
        changes.append(ch)
    changes.sort(key=lambda ch: ch.date or datetime.min.replace(tzinfo=timezone.utc))
    return changes
