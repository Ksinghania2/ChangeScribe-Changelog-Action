"""Config-driven heuristics for parsing and classification."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


@dataclass
class ClassificationConfig:
    default_category: str = "chore"
    keywords: List[Tuple[str, str]] = field(default_factory=lambda: [
        ("fix", r"\b(fix(es|ed)?|bug|crash(es)?|broken|regression|hotfix|race condition|resolve[sd]?)\b"),
        ("perf", r"\b(speed ?up|faster|performance|optimi[sz]e[sd]?|cach(e|ing)|latency|reduce[sd]? (memory|time))\b"),
        ("test", r"\b(unit tests?|tests?|coverage|pytest|unittest)\b"),
        ("docs", r"\b(readme|docs?|documentation|changelog)\b"),
        ("build", r"\b(ci|workflow|docker|dependenc(y|ies)|bump|upgrade|pipeline|deps)\b"),
        ("refactor", r"\b(refactor(ed)?|rename[sd]?|restructure[sd]?|clean ?up|tidy|simplif(y|ied)|extract(ed)?|move[sd]?)\b"),
        ("feature", r"\b(add(s|ed)?|implement(s|ed)?|introduce[sd]?|support(s|ed)?|new|create[sd]?|enable[sd]?|can now)\b"),
    ])
    path_hints: List[Tuple[str, str]] = field(default_factory=lambda: [
        ("docs", r"(^|/)(docs?|README|CHANGELOG)|\.md$|\.rst$"),
        ("test", r"(^|/)(tests?|__tests__|spec)/|(_test|\.test|\.spec)\."),
        ("build", r"(^|/)(\.github|Dockerfile|requirements|package(-lock)?\.json|pyproject|Makefile)"),
    ])
    noise_patterns: List[str] = field(default_factory=lambda: [
        r"^(merge (branch|pull request|remote)|wip\b|fixup!|squash!|update readme\.md$|initial commit$|bump version|release \d|\.+$|minor$|typo$|formatting$|lint$)",
    ])
    rationale_cues: str = (
        r"\b(because|so that|in order to|due to|since|to avoid|to prevent|to allow|to make|to fix|"
        r"previously|used to|instead of|this (change|fixes|means)|which (means|caused|led)|"
        r"users? (can|could|were|had)|was (causing|failing|slow)|otherwise)\b"
    )
    category_titles: Dict[str, str] = field(default_factory=lambda: {
        "breaking": "Breaking Changes",
        "feature": "Added",
        "fix": "Fixed",
        "perf": "Performance",
        "refactor": "Changed",
        "docs": "Documentation",
        "test": "Tests",
        "build": "Build & CI",
        "chore": "Maintenance",
    })


def _load_toml(path: Path) -> Dict[str, Any]:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _read_config_file(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in {".json"}:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    if suffix in {".toml"}:
        return _load_toml(path)
    raise ValueError(f"Unsupported config format: {path}")


def _merge_mapping(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_mapping(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | None = None) -> ClassificationConfig:
    """Load config from a file or from the standard project search paths."""
    candidates: List[Path] = []
    if path:
        candidates.append(Path(path))
    env_path = os.environ.get("CHANGESCRIBE_CONFIG")
    if env_path and path is None:
        candidates.append(Path(env_path))
    candidates.extend([
        Path.cwd() / "changescribe.toml",
        Path.cwd() / "config.toml",
        Path.cwd() / "changescribe.json",
        Path.cwd() / "config.json",
        Path.cwd() / "pyproject.toml",
    ])

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if not candidate.exists():
            continue
        try:
            raw = _read_config_file(candidate)
            if candidate.name == "pyproject.toml":
                raw = raw.get("tool", {}).get("changescribe", {})
            if not raw:
                continue
            cfg = ClassificationConfig()
            # support both a flat dict and a nested "classification" section
            section = raw.get("classification", raw)
            if "keywords" in section and isinstance(section["keywords"], list):
                cfg.keywords = [(str(k), str(v)) for item in section["keywords"] for k, v in item.items()] if section["keywords"] and isinstance(section["keywords"][0], dict) else cfg.keywords
            if "path_hints" in section and isinstance(section["path_hints"], list):
                cfg.path_hints = [(str(k), str(v)) for item in section["path_hints"] for k, v in item.items()] if section["path_hints"] and isinstance(section["path_hints"][0], dict) else cfg.path_hints
            if "noise_patterns" in section:
                cfg.noise_patterns = [str(v) for v in section["noise_patterns"]]
            if "rationale_cues" in section:
                cfg.rationale_cues = str(section["rationale_cues"])
            if "default_category" in section:
                cfg.default_category = str(section["default_category"])
            if "category_titles" in section:
                cfg.category_titles = dict(section["category_titles"])
            return cfg
        except (ValueError, TypeError, json.JSONDecodeError, tomllib.TOMLDecodeError):
            continue
    return ClassificationConfig()
