"""Stage 3 - turn processed changes into human-readable changelog entries.

Two interchangeable backends:
  * AnthropicSummarizer - LLM call through the Messages API (best quality).
  * HeuristicSummarizer - deterministic, offline, zero-cost fallback.
`get_summarizer("auto")` picks the LLM when ANTHROPIC_API_KEY is set.
"""
from __future__ import annotations

import json
import os
import re
from typing import List, Optional

import requests

from .models import CATEGORIES, Change, Entry
from .parser import chunk

DEFAULT_MODEL = "claude-sonnet-5-5"

SYSTEM_PROMPT = """You are a technical writer who maintains a project's changelog.
You receive a JSON list of changes made during a sprint. Each has: id, category, scope,
title, why (rationale taken from commit bodies / PR discussion), files, breaking.

Write ONE entry per change (merge entries only if they are clearly the same work).
Rules:
- "summary": one plain-English sentence describing what is different for a user or
  integrator. Never just restate a function name; no leading verbs like 'Fixed'.
- "impact": one short sentence on WHY it matters / what problem it solves, using only
  facts present in the input. Use "" if the input gives no reason. Never invent facts.
- Keep "category" as given unless it is clearly wrong; allowed values: %s.
- Keep "refs" exactly as the input ids (and issue numbers if present).
Return ONLY a JSON array of objects with keys: category, summary, impact, refs, scope.""" % ", ".join(CATEGORIES)


class Summarizer:
    name = "base"

    def summarize(self, changes: List[Change]) -> List[Entry]:  # pragma: no cover
        raise NotImplementedError


# ------------------------------------------------------------------ heuristic
def _clean_title(title: str) -> str:
    t = re.sub(r"\s+", " ", title).strip().rstrip(".")
    return t[0].upper() + t[1:] if t else t


class HeuristicSummarizer(Summarizer):
    name = "heuristic"

    def summarize(self, changes: List[Change]) -> List[Entry]:
        entries = []
        for ch in changes:
            refs = [ch.id] + ch.issues
            cat = "breaking" if ch.breaking else ch.category
            impact = ch.rationale
            if impact and impact.lower().startswith(ch.title.lower()[:30]):
                impact = ""
            entries.append(Entry(category=cat, summary=_clean_title(ch.title),
                                 impact=impact, refs=refs, scope=ch.scope))
        return entries


# ------------------------------------------------------------------ LLM
class AnthropicSummarizer(Summarizer):
    name = "anthropic"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 session: Optional[requests.Session] = None, fallback: Optional[Summarizer] = None,
                 base_url: str = "https://api.anthropic.com"):
        self.key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        self.model = model or os.environ.get("CHANGESCRIBE_MODEL", DEFAULT_MODEL)
        self.s = session or requests.Session()
        self.url = base_url.rstrip("/") + "/v1/messages"
        self.fallback = fallback or HeuristicSummarizer()

    def _call(self, payload: str) -> str:
        r = self.s.post(self.url, timeout=90, headers={
            "x-api-key": self.key, "anthropic-version": "2023-06-01",
            "content-type": "application/json"},
            json={"model": self.model, "max_tokens": 2000, "temperature": 0.2,
                  "system": SYSTEM_PROMPT,
                  "messages": [{"role": "user", "content": payload}]})
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json().get("content", []))

    @staticmethod
    def _parse(text: str) -> list:
        text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
        start, end = text.find("["), text.rfind("]")
        if start < 0 or end < 0:
            raise ValueError("no JSON array in model output")
        return json.loads(text[start:end + 1])

    def summarize(self, changes: List[Change]) -> List[Entry]:
        entries: List[Entry] = []
        for group in chunk(changes):
            payload = json.dumps([{
                "id": c.id, "category": "breaking" if c.breaking else c.category, "scope": c.scope,
                "title": c.title, "why": c.rationale, "files": c.files[:8],
                "issues": c.issues, "breaking": c.breaking} for c in group], ensure_ascii=False)
            try:
                items = self._parse(self._call(payload))
                for it in items:
                    cat = it.get("category", "chore")
                    entries.append(Entry(category=cat if cat in CATEGORIES else "chore",
                                         summary=str(it.get("summary", "")).strip(),
                                         impact=str(it.get("impact", "")).strip(),
                                         refs=[str(r) for r in it.get("refs", [])],
                                         scope=str(it.get("scope", ""))))
            except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError) as exc:
                print(f"[changescribe] LLM call failed ({exc}); using heuristic for this chunk")
                entries.extend(self.fallback.summarize(group))
        return [e for e in entries if e.summary]


def get_summarizer(backend: str = "auto") -> Summarizer:
    backend = (backend or "auto").lower()
    if backend == "heuristic":
        return HeuristicSummarizer()
    if backend == "anthropic":
        return AnthropicSummarizer()
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicSummarizer()
    return HeuristicSummarizer()
