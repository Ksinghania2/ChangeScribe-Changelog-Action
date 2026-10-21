"""Plain data containers shared by every stage of the pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional

CATEGORIES = ["breaking", "feature", "fix", "perf", "refactor", "docs", "test", "build", "chore"]

CATEGORY_TITLES = {
    "breaking": "Breaking Changes",
    "feature": "Added",
    "fix": "Fixed",
    "perf": "Performance",
    "refactor": "Changed",
    "docs": "Documentation",
    "test": "Tests",
    "build": "Build & CI",
    "chore": "Maintenance",
}


@dataclass
class Change:
    """One unit of work: a merged pull request, or a direct commit."""

    id: str                      # short sha, or "PR#12"
    title: str                   # commit subject / PR title
    body: str = ""               # commit body / PR description
    author: str = ""
    date: Optional[datetime] = None
    files: List[str] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    discussion: List[str] = field(default_factory=list)   # PR / review comments
    labels: List[str] = field(default_factory=list)
    pr_number: Optional[int] = None
    url: str = ""
    # filled by the parser
    category: str = "chore"
    scope: str = ""
    breaking: bool = False
    rationale: str = ""
    issues: List[str] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["date"] = self.date.isoformat() if self.date else None
        return d


@dataclass
class Entry:
    """A finished changelog line produced by a summarizer."""

    category: str
    summary: str
    impact: str = ""
    refs: List[str] = field(default_factory=list)
    scope: str = ""

    def to_dict(self):
        return asdict(self)
