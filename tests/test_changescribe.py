import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from changescribe import collector, parser, renderer, summarizer, pipeline  # noqa: E402
from changescribe.models import Change, Entry  # noqa: E402


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class FakeResp:
    def __init__(self, data, status=200, links=None, headers=None):
        self._d, self.status_code, self.links, self.headers = data, status, links or {}, headers or {}

    def json(self):
        return self._d

    def raise_for_status(self):
        if self.status_code >= 400:
            raise collector.requests.HTTPError(str(self.status_code))


class FakeGitHub:
    """Routes REST paths to canned JSON so no network is needed."""
    def __init__(self):
        self.headers = {}
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.routes = {
            "/repos/o/r/pulls": [{"number": 7, "title": "Add CSV export", "merged_at": now,
                                  "body": "Finance asked for it because month-end reports were manual.",
                                  "user": {"login": "ana"}, "labels": [{"name": "enhancement"}],
                                  "html_url": "https://github.com/o/r/pull/7", "merge_commit_sha": "m1"}],
            "/repos/o/r/pulls/7/files": [{"filename": "export.py", "additions": 30, "deletions": 2}],
            "/repos/o/r/issues/7/comments": [{"body": "Please keep headers stable so scripts keep working.", "user": {"type": "User"}},
                                             {"body": "CI passed", "user": {"type": "Bot"}}],
            "/repos/o/r/pulls/7/comments": [],
            "/repos/o/r/pulls/7/commits": [{"sha": "c1"}],
            "/repos/o/r/commits": [
                {"sha": "c1", "parents": [1], "commit": {"message": "inside pr", "author": {"name": "ana", "date": now}}},
                {"sha": "d2", "parents": [1], "html_url": "u", "author": {"login": "bo"},
                 "commit": {"message": "fix: stop crash on empty input\n\nIt raised IndexError because the list was empty.",
                            "author": {"name": "bo", "date": now}}}],
            "/repos/o/r/commits/d2": {"files": [{"filename": "a.py", "additions": 1, "deletions": 1}]},
        }

    def get(self, url, params=None, timeout=None):
        path = url.replace("https://api.github.com", "")
        if path not in self.routes:
            return FakeResp({}, 404)
        return FakeResp(self.routes[path])


class FakeLLM:
    def __init__(self, text=None, fail=False):
        self.text, self.fail, self.calls = text, fail, 0

    def post(self, url, **kw):
        self.calls += 1
        if self.fail:
            raise collector.requests.ConnectionError("boom")
        return FakeResp({"content": [{"type": "text", "text": self.text}]})


class ParserTests(unittest.TestCase):
    def test_since(self):
        now = datetime(2026, 10, 22, tzinfo=timezone.utc)
        self.assertEqual(collector.parse_since("14d", now), now - timedelta(days=14))
        self.assertEqual(collector.parse_since("2w", now), now - timedelta(weeks=2))
        self.assertEqual(collector.parse_since("2026-10-01").day, 1)
        self.assertIsNone(collector.parse_since(None))

    def test_conventional_and_breaking(self):
        c = parser.classify(Change(id="a", title="feat(api)!: drop v1 routes"))
        self.assertEqual((c.category, c.scope, c.breaking, c.title), ("feature", "api", True, "drop v1 routes"))

    def test_body_breaking_change(self):
        c = parser.classify(Change(id="a", title="Drop py38", body="BREAKING CHANGE: need 3.9+"))
        self.assertTrue(c.breaking)
        self.assertEqual(c.rationale, "need 3.9+")

    def test_keyword_and_label_and_path(self):
        self.assertEqual(parser.classify(Change(id="a", title="Fixes crash on start")).category, "fix")
        self.assertEqual(parser.classify(Change(id="a", title="Add unit tests for x")).category, "test")
        self.assertEqual(parser.classify(Change(id="a", title="Polish", labels=["bug"])).category, "fix")
        self.assertEqual(parser.classify(Change(id="a", title="Polish", files=["docs/a.md"])).category, "docs")
        self.assertEqual(parser.classify(Change(id="a", title="chore(deps): bump x")).category, "build")

    def test_noise(self):
        keep = [Change(id="1", title="Add search"), Change(id="2", title="Merge branch 'main'"),
                Change(id="3", title="WIP"), Change(id="4", title="fixup! x")]
        self.assertEqual([c.id for c in parser.process(keep)], ["1"])

    def test_rationale_prefers_cued_sentences(self):
        c = Change(id="a", title="x", body="Some intro text here. It was slow because rows were loaded twice.\n\nSigned-off-by: a")
        self.assertIn("because rows", parser.extract_rationale(c))
        self.assertNotIn("Signed-off", parser.extract_rationale(c))

    def test_rationale_uses_pr_discussion_and_issue_refs(self):
        c = parser.classify(Change(id="PR#1", title="Add export", body="Fixes #9",
                                   discussion=["Keep headers stable so that scripts do not break."]))
        self.assertIn("scripts", c.rationale)
        self.assertEqual(c.issues, ["#9"])

    def test_chunking_respects_budget(self):
        ch = [Change(id=str(i), title="t" * 100, rationale="r" * 100) for i in range(50)]
        groups = parser.chunk(ch, max_chars=2000)
        self.assertGreater(len(groups), 1)
        self.assertEqual(sum(len(g) for g in groups), 50)


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.entries = [Entry("feature", "Add export", "Finance needs it", ["PR#7"]),
                        Entry("fix", "Stop crash", "", ["abc1234"], scope="api")]

    def test_section_order_and_content(self):
        md = renderer.render_section(self.entries, "1.0.0")
        self.assertLess(md.index("### Added"), md.index("### Fixed"))
        self.assertIn("*Why:* Finance needs it.", md)
        self.assertIn("**api:** Stop crash.", md)

    def test_empty(self):
        self.assertIn("No user-facing", renderer.render_section([], "1.0.0"))

    def test_changelog_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "CHANGELOG.md")
            renderer.update_changelog(p, renderer.render_section(self.entries, "1.1.0"))
            renderer.update_changelog(p, renderer.render_section(self.entries[:1], "1.2.0"))
            renderer.update_changelog(p, renderer.render_section(self.entries, "1.2.0"))
            text = _read(p)
            self.assertEqual(text.count("## [1.2.0]"), 1)
            self.assertLess(text.index("[1.2.0]"), text.index("[1.1.0]"))
            self.assertIn("Stop crash", text)

    def test_readme_markers(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "README.md")
            with open(p, "w") as fh:
                fh.write("# App\n\nIntro\n")
            renderer.update_readme(p, "first")
            renderer.update_readme(p, "second")
            t = _read(p)
            self.assertEqual(t.count(renderer.START), 1)
            self.assertIn("second", t)
            self.assertNotIn("first", t)
            self.assertTrue(t.startswith("# App"))

    def test_html(self):
        h = renderer.to_html("### Added\n\n- **x:** a <b>\n  - *Why:* because")
        self.assertIn("<h3>", h)
        self.assertIn("&lt;b&gt;", h)
        self.assertIn("<em>Why:</em>", h)


class CollectorTests(unittest.TestCase):
    def test_local_repo(self):
        import make_demo_repo
        with tempfile.TemporaryDirectory() as d:
            make_demo_repo.build(d)
            ch = collector.collect_local(d, collector.parse_since("30d"))
            self.assertEqual(len(ch), len(make_demo_repo.COMMITS))
            self.assertTrue(ch[0].files)
            self.assertLess(ch[0].date, ch[-1].date)

    def test_github_prs_and_commits(self):
        gh = collector.GitHubClient(session=FakeGitHub())
        ch = collector.collect_github("o/r", collector.parse_since("7d"), client=gh)
        ids = [c.id for c in ch]
        self.assertIn("PR#7", ids)
        self.assertIn("d2"[:7], ids)
        self.assertNotIn("c1", ids)                      # commit already covered by PR
        pr = next(c for c in ch if c.id == "PR#7")
        self.assertEqual(pr.additions, 30)
        self.assertEqual(len(pr.discussion), 1)           # bot comment dropped

    def test_github_404(self):
        gh = collector.GitHubClient(session=FakeGitHub())
        with self.assertRaises(RuntimeError):
            gh.get("/repos/none/none")


class SummarizerTests(unittest.TestCase):
    def changes(self):
        return parser.process([Change(id="a1", title="feat: add export", body="Finance needs it because reports were manual.")])

    def test_heuristic(self):
        e = summarizer.HeuristicSummarizer().summarize(self.changes())
        self.assertEqual(e[0].category, "feature")
        self.assertIn("because", e[0].impact)

    def test_llm_parses_fenced_json(self):
        fake = FakeLLM('```json\n[{"category":"feature","summary":"Finance can export CSV","impact":"Ends manual reports","refs":["a1"],"scope":""}]\n```')
        s = summarizer.AnthropicSummarizer(api_key="k", session=fake)
        e = s.summarize(self.changes())
        self.assertEqual(e[0].summary, "Finance can export CSV")
        self.assertEqual(fake.calls, 1)

    def test_llm_falls_back_on_error_and_bad_json(self):
        for fake in (FakeLLM(fail=True), FakeLLM("sorry, no json here")):
            s = summarizer.AnthropicSummarizer(api_key="k", session=fake)
            e = s.summarize(self.changes())
            self.assertEqual(e[0].category, "feature")

    def test_unknown_category_normalised(self):
        fake = FakeLLM('[{"category":"weird","summary":"x","impact":"","refs":[]}]')
        e = summarizer.AnthropicSummarizer(api_key="k", session=fake).summarize(self.changes())
        self.assertEqual(e[0].category, "chore")

    def test_requires_key(self):
        old = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with self.assertRaises(ValueError):
                summarizer.AnthropicSummarizer()
            self.assertEqual(summarizer.get_summarizer("auto").name, "heuristic")
        finally:
            if old:
                os.environ["ANTHROPIC_API_KEY"] = old


class PipelineAndWebTests(unittest.TestCase):
    def test_pipeline_with_injected_changes(self):
        res = pipeline.run(changes=[Change(id="1", title="fix: crash", body="It crashed because of None."),
                                    Change(id="2", title="WIP")], backend="heuristic", version="9.9.9")
        self.assertEqual((res.raw_count, len(res.entries)), (2, 1))
        self.assertIn("[9.9.9]", res.markdown)

    def test_cli_writes_files(self):
        import make_demo_repo
        from changescribe import cli
        with tempfile.TemporaryDirectory() as d:
            repo = os.path.join(d, "r")
            make_demo_repo.build(repo)
            cl, rd = os.path.join(d, "CHANGELOG.md"), os.path.join(d, "README.md")
            code = cli.main(["generate", "--repo", repo, "--since", "30d", "--backend", "heuristic",
                             "--changelog", cl, "--readme", rd, "--release", "1.0.0"])
            self.assertEqual(code, 0)
            self.assertIn("## [1.0.0]", _read(cl))
            self.assertIn(renderer.START, _read(rd))

    def test_web(self):
        from changescribe.webapp import create_app
        c = create_app().test_client()
        self.assertEqual(c.get("/").status_code, 200)
        self.assertEqual(c.get("/healthz").get_json()["status"], "ok")
        r = c.post("/", data={"repo": "not a repo"})
        self.assertIn("owner/name", r.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
