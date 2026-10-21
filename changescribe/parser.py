"""Stage 2 - clean, classify and chunk the raw history.

The goal is to hand the LLM *intent* (why a change was made) rather than raw
diffs, so we extract rationale sentences from commit bodies, PR descriptions
and review discussion, drop noise, and pack the result into token-bounded chunks.
"""
from __future__ import annotations

import re
from typing import Iterable, List

from .models import Change

CONVENTIONAL = re.compile(
    r"^(?P<type>feat|feature|fix|perf|refactor|docs?|test|tests|build|ci|chore|style|revert)"
    r"(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?:\s*(?P<desc>.+)$", re.I)

TYPE_MAP = {"feat": "feature", "feature": "feature", "fix": "fix", "perf": "perf",
            "refactor": "refactor", "doc": "docs", "docs": "docs", "test": "test",
            "tests": "test", "build": "build", "ci": "build", "chore": "chore",
            "style": "chore", "revert": "fix"}

KEYWORDS = [   # (category, regex) - first match wins, used when no conventional prefix
    ("fix", r"\b(fix(es|ed)?|bug|crash(es)?|broken|regression|hotfix|race condition|resolve[sd]?)\b"),
    ("perf", r"\b(speed ?up|faster|performance|optimi[sz]e[sd]?|cach(e|ing)|latency|reduce[sd]? (memory|time))\b"),
    ("test", r"\b(unit tests?|tests?|coverage|pytest|unittest)\b"),
    ("docs", r"\b(readme|docs?|documentation|changelog)\b"),
    ("build", r"\b(ci|workflow|docker|dependenc(y|ies)|bump|upgrade|pipeline|deps)\b"),
    ("refactor", r"\b(refactor(ed)?|rename[sd]?|restructure[sd]?|clean ?up|tidy|simplif(y|ied)|extract(ed)?|move[sd]?)\b"),
    ("feature", r"\b(add(s|ed)?|implement(s|ed)?|introduce[sd]?|support(s|ed)?|new|create[sd]?|enable[sd]?|can now)\b"),
]

NOISE_TITLE = re.compile(
    r"^(merge (branch|pull request|remote)|wip\b|fixup!|squash!|update readme\.md$|initial commit$|"
    r"bump version|release \d|\.+$|minor$|typo$|formatting$|lint$)", re.I)

RATIONALE_CUES = re.compile(
    r"\b(because|so that|in order to|due to|since|to avoid|to prevent|to allow|to make|to fix|"
    r"previously|used to|instead of|this (change|fixes|means)|which (means|caused|led)|"
    r"users? (can|could|were|had)|was (causing|failing|slow)|otherwise)\b", re.I)

ISSUE_REF = re.compile(r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)?\s*#(\d+)", re.I)
BREAKING_BODY = re.compile(r"^BREAKING[ -]CHANGE:\s*(.+)$", re.I | re.M)
TRAILER = re.compile(r"^(signed-off-by|co-authored-by|reviewed-by|change-id):", re.I)
CODE_FENCE = re.compile(r"```.*?```", re.S)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)

PATH_HINTS = [("docs", r"(^|/)(docs?|README|CHANGELOG)|\.md$|\.rst$"),
              ("test", r"(^|/)(tests?|__tests__|spec)/|(_test|\.test|\.spec)\."),
              ("build", r"(^|/)(\.github|Dockerfile|requirements|package(-lock)?\.json|pyproject|Makefile)")]


def _sentences(text: str) -> List[str]:
    text = HTML_COMMENT.sub(" ", CODE_FENCE.sub(" ", text or ""))
    lines = [l.strip(" -*>\t") for l in text.splitlines()
             if l.strip() and not TRAILER.match(l.strip()) and not l.strip().startswith("#")]
    joined = " ".join(lines)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", joined) if len(s.strip()) > 15]


def extract_rationale(change: Change, max_sentences: int = 2) -> str:
    """Pick the sentences that explain *why*: body/PR text first, then discussion."""
    pool = _sentences(change.body) + [s for c in change.discussion for s in _sentences(c)]
    cued = [s for s in pool if RATIONALE_CUES.search(s)]
    chosen = (cued or pool)[:max_sentences]
    return " ".join(chosen)[:400]


def is_noise(change: Change) -> bool:
    if NOISE_TITLE.search(change.title.strip()):
        return True
    if change.title.lower().startswith("revert \"merge"):
        return True
    if not change.title.strip():
        return True
    return False


def classify(change: Change) -> Change:
    title = change.title.strip()
    m = CONVENTIONAL.match(title)
    if m:
        change.category = TYPE_MAP[m.group("type").lower()]
        change.scope = (m.group("scope") or "").strip()
        change.breaking = bool(m.group("bang"))
        change.title = m.group("desc").strip()
        if change.category == "chore" and change.scope.lower() in ("deps", "deps-dev", "build", "ci", "docker"):
            change.category = "build"
    else:
        label_map = {**TYPE_MAP, "bug": "fix", "bugfix": "fix", "enhancement": "feature",
                     "documentation": "docs", "performance": "perf", "dependencies": "build"}
        label_hit = next((label_map[l.lower()] for l in change.labels if l.lower() in label_map), None)
        if label_hit:
            change.category = label_hit
        else:
            low = title.lower()
            change.category = next((cat for cat, rx in KEYWORDS if re.search(rx, low)), None) or ""
            if not change.category:
                change.category = _from_paths(change.files) or "chore"
    if BREAKING_BODY.search(change.body) or "breaking" in [l.lower() for l in change.labels]:
        change.breaking = True
    if change.breaking:
        mb = BREAKING_BODY.search(change.body)
        if mb:
            change.rationale = mb.group(1).strip()
    change.issues = sorted({f"#{n}" for n in ISSUE_REF.findall(f"{change.title} {change.body}")})
    if not change.rationale:
        change.rationale = extract_rationale(change)
    return change


def _from_paths(files: Iterable[str]) -> str:
    files = list(files)
    if not files:
        return ""
    for cat, rx in PATH_HINTS:
        if all(re.search(rx, f) for f in files):
            return cat
    return ""


def process(changes: List[Change], drop_noise: bool = True) -> List[Change]:
    out = []
    for ch in changes:
        if drop_noise and is_noise(ch):
            continue
        out.append(classify(ch))
    return out


def chunk(changes: List[Change], max_chars: int = 6000) -> List[List[Change]]:
    """Greedy packing so every LLM request stays inside a predictable budget."""
    chunks, cur, size = [], [], 0
    for ch in changes:
        cost = len(ch.title) + len(ch.rationale) + 80
        if cur and size + cost > max_chars:
            chunks.append(cur)
            cur, size = [], 0
        cur.append(ch)
        size += cost
    if cur:
        chunks.append(cur)
    return chunks
