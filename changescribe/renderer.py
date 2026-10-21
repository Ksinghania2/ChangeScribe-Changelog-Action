"""Stage 4 - render entries as Markdown and write them into CHANGELOG / README."""
from __future__ import annotations

import os
import re
from datetime import date
from typing import List, Optional

from .models import CATEGORIES, CATEGORY_TITLES, Entry

START = "<!-- changescribe:start -->"
END = "<!-- changescribe:end -->"
ORDER = ["breaking", "feature", "fix", "perf", "refactor", "docs", "test", "build", "chore"]


def _read(path: str, default: str) -> str:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _line(e: Entry, links: Optional[dict] = None) -> str:
    scope = f"**{e.scope}:** " if e.scope else ""
    refs = ""
    if e.refs:
        shown = [f"[{r}]({links[r]})" if links and links.get(r) else r for r in e.refs]
        refs = f" ({', '.join(shown)})"
    text = f"- {scope}{e.summary.rstrip('.')}.{refs}"
    if e.impact:
        text += f"\n  - *Why:* {e.impact.rstrip('.')}."
    return text


def render_section(entries: List[Entry], version: str = "Unreleased", day: Optional[date] = None,
                   links: Optional[dict] = None, heading_level: int = 2,
                   include_minor: bool = True) -> str:
    day = day or date.today()
    h = "#" * heading_level
    lines = [f"{h} [{version}] - {day.isoformat()}", ""]
    if not entries:
        return "\n".join(lines + ["_No user-facing changes this period._", ""])
    by_cat = {c: [] for c in ORDER}
    for e in entries:
        by_cat.setdefault(e.category if e.category in by_cat else "chore", []).append(e)
    minor = {"docs", "test", "build", "chore"}
    for cat in ORDER:
        if not by_cat[cat] or (not include_minor and cat in minor):
            continue
        lines += [f"{h}# {CATEGORY_TITLES[cat]}", ""]
        lines += [_line(e, links) for e in by_cat[cat]]
        lines.append("")
    return "\n".join(lines)


def build_summary_line(entries: List[Entry]) -> str:
    counts = {}
    for e in entries:
        counts[e.category] = counts.get(e.category, 0) + 1
    parts = [f"{counts[c]} {CATEGORY_TITLES[c].lower()}" for c in ORDER if counts.get(c)]
    return "This period: " + ", ".join(parts) + "." if parts else ""


def update_changelog(path: str, section: str) -> str:
    """Insert `section` right under the title; idempotent for the same version heading."""
    header = "# Changelog\n\nAll notable changes to this project are documented here.\n\n"
    existing = _read(path, header)
    first_heading = section.splitlines()[0]
    if first_heading in existing:      # same version already present -> replace that block
        pattern = re.compile(re.escape(first_heading) + r".*?(?=^## \[|\Z)", re.S | re.M)
        new = pattern.sub(lambda _: section.rstrip() + "\n\n", existing, count=1)
    else:
        m = re.search(r"^## \[", existing, re.M)
        if m:
            new = existing[:m.start()] + section.rstrip() + "\n\n" + existing[m.start():]
        else:
            new = existing.rstrip() + "\n\n" + section.rstrip() + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    return new


def update_readme(path: str, section: str, title: str = "## Recent changes") -> str:
    """Replace the managed block between markers; create it at the end if missing."""
    block = f"{START}\n{title}\n\n{section.strip()}\n{END}"
    text = _read(path, "# Project\n")
    if START in text and END in text:
        new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    else:
        new = text.rstrip() + "\n\n" + block + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    return new


def to_html(markdown_text: str) -> str:
    """Minimal Markdown -> HTML for the web preview (headings, bullets, bold, italics, links)."""
    import html
    out, in_ul, depth = [], 0, 0

    def inline(s):
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
        return re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)

    for raw in markdown_text.splitlines():
        m = re.match(r"^(\s*)- (.*)$", raw)
        if m:
            d = 1 if len(m.group(1)) >= 2 else 0
            while in_ul < d + 1:
                out.append("<ul>"); in_ul += 1
            while in_ul > d + 1:
                out.append("</ul>"); in_ul -= 1
            out.append(f"<li>{inline(m.group(2))}</li>")
            continue
        while in_ul:
            out.append("</ul>"); in_ul -= 1
        h = re.match(r"^(#{1,6})\s+(.*)$", raw)
        if h:
            n = len(h.group(1))
            out.append(f"<h{n}>{inline(h.group(2))}</h{n}>")
        elif raw.strip():
            out.append(f"<p>{inline(raw)}</p>")
    while in_ul:
        out.append("</ul>"); in_ul -= 1
    return "\n".join(out)
