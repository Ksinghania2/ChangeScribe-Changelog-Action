"""Stage 2 - clean, classify and chunk the raw history.

The goal is to hand the LLM *intent* (why a change was made) rather than raw
diffs, so we extract rationale sentences from commit bodies, PR descriptions
and review discussion, drop noise, and pack the result into token-bounded chunks.
"""
from __future__ import annotations

import re
from typing import Iterable, List, Optional

from .config import ClassificationConfig, load_config
from .models import Change

CONVENTIONAL = re.compile(
    r"^(?P<type>feat|feature|fix|perf|refactor|docs?|test|tests|build|ci|chore|style|revert)"
    r"(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?:\s*(?P<desc>.+)$", re.I)

TYPE_MAP = {"feat": "feature", "feature": "feature", "fix": "fix", "perf": "perf",
            "refactor": "refactor", "doc": "docs", "docs": "docs", "test": "test",
            "tests": "test", "build": "build", "ci": "build", "chore": "chore",
            "style": "chore", "revert": "fix"}

DEFAULT_CONFIG = load_config()
KEYWORDS = DEFAULT_CONFIG.keywords
NOISE_TITLE = re.compile("|".join(DEFAULT_CONFIG.noise_patterns), re.I)
RATIONALE_CUES = re.compile(DEFAULT_CONFIG.rationale_cues, re.I)

ISSUE_REF = re.compile(r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)?\s*#(\d+)", re.I)
BREAKING_BODY = re.compile(r"^BREAKING[ -]CHANGE:\s*(.+)$", re.I | re.M)
TRAILER = re.compile(r"^(signed-off-by|co-authored-by|reviewed-by|change-id):", re.I)
CODE_FENCE = re.compile(r"```.*?```", re.S)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)

PATH_HINTS = DEFAULT_CONFIG.path_hints


def _sentences(text: str) -> List[str]:
    text = HTML_COMMENT.sub(" ", CODE_FENCE.sub(" ", text or ""))
    lines = [l.strip(" -*>\t") for l in text.splitlines()
             if l.strip() and not TRAILER.match(l.strip()) and not l.strip().startswith("#")]
    joined = " ".join(lines)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", joined) if len(s.strip()) > 15]


def extract_rationale(change: Change, max_sentences: int = 2, config: Optional[ClassificationConfig] = None) -> str:
    """Pick the sentences that explain *why*: body/PR text first, then discussion."""
    cfg = config or DEFAULT_CONFIG
    cues = re.compile(cfg.rationale_cues, re.I)
    pool = _sentences(change.body) + [s for c in change.discussion for s in _sentences(c)]
    cued = [s for s in pool if cues.search(s)]
    chosen = (cued or pool)[:max_sentences]
    return " ".join(chosen)[:400]


def is_noise(change: Change, config: Optional[ClassificationConfig] = None) -> bool:
    cfg = config or DEFAULT_CONFIG
    pattern = re.compile("|".join(cfg.noise_patterns), re.I)
    if pattern.search(change.title.strip()):
        return True
    if change.title.lower().startswith("revert \"merge"):
        return True
    if not change.title.strip():
        return True
    return False


def classify(change: Change, config: Optional[ClassificationConfig] = None) -> Change:
    cfg = config or DEFAULT_CONFIG
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
            change.category = next((cat for cat, rx in cfg.keywords if re.search(rx, low)), None) or ""
            if not change.category:
                change.category = _from_paths(change.files, config=cfg) or cfg.default_category
    if BREAKING_BODY.search(change.body) or "breaking" in [l.lower() for l in change.labels]:
        change.breaking = True
    if change.breaking:
        mb = BREAKING_BODY.search(change.body)
        if mb:
            change.rationale = mb.group(1).strip()
    change.issues = sorted({f"#{n}" for n in ISSUE_REF.findall(f"{change.title} {change.body}")})
    if not change.rationale:
        change.rationale = extract_rationale(change, config=cfg)
    return change


def _from_paths(files: Iterable[str], config: Optional[ClassificationConfig] = None) -> str:
    cfg = config or DEFAULT_CONFIG
    files = list(files)
    if not files:
        return ""
    for cat, rx in cfg.path_hints:
        if all(re.search(rx, f) for f in files):
            return cat
    return ""


def process(changes: List[Change], drop_noise: bool = True, config: Optional[ClassificationConfig] = None) -> List[Change]:
    cfg = config or DEFAULT_CONFIG
    out = []
    for ch in changes:
        if drop_noise and is_noise(ch, config=cfg):
            continue
        out.append(classify(ch, config=cfg))
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
