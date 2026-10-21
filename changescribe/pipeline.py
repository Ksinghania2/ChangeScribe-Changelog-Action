"""End-to-end orchestration: collect -> parse -> summarize -> render."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from . import collector, parser, renderer
from .models import Change, Entry
from .summarizer import Summarizer, get_summarizer


@dataclass
class Result:
    raw_count: int
    changes: List[Change]
    entries: List[Entry]
    markdown: str
    backend: str


def run(*, repo_path: Optional[str] = None, github_repo: Optional[str] = None,
        since: Optional[str] = "14d", until: Optional[str] = None, token: Optional[str] = None,
        backend: str = "auto", version: str = "Unreleased", branch: Optional[str] = None,
        include_minor: bool = True, summarizer: Optional[Summarizer] = None,
        changes: Optional[List[Change]] = None) -> Result:
    since_dt, until_dt = collector.parse_since(since), collector.parse_since(until)
    if changes is None:
        if github_repo:
            changes = collector.collect_github(github_repo, since_dt, until_dt, token=token, branch=branch)
        else:
            changes = collector.collect_local(repo_path or ".", since_dt, until_dt,
                                              rev_range=branch or "HEAD")
    raw = len(changes)
    processed = parser.process(changes)
    summ = summarizer or get_summarizer(backend)
    entries = summ.summarize(processed)
    links = {c.id: c.url for c in processed if c.url}
    md = renderer.render_section(entries, version=version, day=date.today(), links=links,
                                 include_minor=include_minor)
    return Result(raw, processed, entries, md, summ.name)
