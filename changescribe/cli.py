"""Command line interface:  python -m changescribe generate --since 14d"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__, pipeline, renderer


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="changescribe",
                                description="Generate changelog / README updates from git history.")
    p.add_argument("--version", action="version", version=f"changescribe {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="collect history and write documentation")
    src = g.add_mutually_exclusive_group()
    src.add_argument("--repo", default=".", help="path to a local git clone (default: .)")
    src.add_argument("--github", metavar="OWNER/NAME", help="read from the GitHub API instead")
    g.add_argument("--since", default="14d", help="14d, 2w, 36h or ISO date (default 14d)")
    g.add_argument("--until", default=None)
    g.add_argument("--branch", default=None, help="branch / rev range to read")
    g.add_argument("--backend", choices=["auto", "anthropic", "heuristic"], default="auto")
    g.add_argument("--release", default="Unreleased", help="version heading, e.g. 1.2.0")
    g.add_argument("--changelog", default=None, help="CHANGELOG file to update")
    g.add_argument("--readme", default=None, help="README file whose managed block is refreshed")
    g.add_argument("--no-minor", action="store_true", help="hide docs/test/build/chore entries")
    g.add_argument("--json", action="store_true", help="print structured JSON instead of Markdown")
    g.add_argument("--dry-run", action="store_true", help="print only, never write files")
    sub.add_parser("serve", help="start the web UI").add_argument("--port", type=int, default=5000)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "serve":
        from .webapp import create_app
        create_app().run(host="0.0.0.0", port=args.port)
        return 0
    token = os.environ.get("GITHUB_TOKEN")
    try:
        res = pipeline.run(repo_path=args.repo, github_repo=args.github, since=args.since,
                           until=args.until, token=token, backend=args.backend, version=args.release,
                           branch=args.branch, include_minor=not args.no_minor)
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"backend": res.backend, "raw_commits": res.raw_count,
                          "entries": [e.to_dict() for e in res.entries]}, indent=2))
    else:
        print(res.markdown)
    if args.dry_run:
        return 0
    if args.changelog:
        renderer.update_changelog(args.changelog, res.markdown)
        print(f"[changescribe] updated {args.changelog}", file=sys.stderr)
    if args.readme:
        summary = renderer.build_summary_line(res.entries)
        body = res.markdown if not summary else f"{summary}\n\n{res.markdown}"
        renderer.update_readme(args.readme, body)
        print(f"[changescribe] updated {args.readme}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
