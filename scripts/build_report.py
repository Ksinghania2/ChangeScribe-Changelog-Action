"""Fill the university mini-project template with the ChangeScribe report."""
import copy
import json
import os
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = os.path.dirname(__file__)
ASSETS = os.path.join(HERE, "..", "docs", "assets")
TEMPLATE, OUT = sys.argv[1], sys.argv[2]
M = json.load(open(os.path.join(ASSETS, "metrics.json")))

doc = Document(TEMPLATE)
P = doc.paragraphs

# ---------------------------------------------------------------- cover page
def set_text(par, text):
    runs = par.runs
    runs[0].text = text
    for r in runs[1:]:
        r.text = ""

set_text(P[2], "ChangeScribe: Automated README & Documentation Generator from Code Diff History")
for r in P[2].runs:
    r.font.size = Pt(20)          # keeps the long title on two lines so the cover stays on one page
set_text(P[11], "Kshitij Singhania")
set_text(P[12], "Registration number: 23FE10CCE00152")

# ---------------------------------------------------------------- remove template instructions
for par in P[22:]:
    par._element.getparent().remove(par._element)

body = doc.element.body
sect = body.find(qn("w:sectPr"))


def _fmt(run, size=12, bold=False, italic=False):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic


def para(text="", size=12, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=6, before=0, keep=False):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = 1.15
    if keep:
        p.paragraph_format.keep_with_next = True
    if text:
        # allow **bold** inline segments
        parts = text.split("**")
        for i, seg in enumerate(parts):
            if seg:
                _fmt(p.add_run(seg), size, bold or i % 2 == 1, italic)
    return p


def heading(text):
    return para(text, size=13.5, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, after=6, before=12, keep=True)


def sub(text):
    return para(text, size=12, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, after=3, before=6, keep=True)


def bullet(text, level=0):
    p = para(text, after=3, align=WD_ALIGN_PARAGRAPH.LEFT)
    pf = p.paragraph_format
    pf.left_indent = Inches(0.35 + 0.3 * level)
    pf.first_line_indent = Inches(-0.2)
    p.runs[0].text = "\u2022  " + p.runs[0].text if p.runs else None
    return p


def numbered(n, text):
    p = para(text, after=3, align=WD_ALIGN_PARAGRAPH.LEFT)
    p.paragraph_format.left_indent = Inches(0.4)
    p.paragraph_format.first_line_indent = Inches(-0.25)
    p.runs[0].text = f"{n}.  " + p.runs[0].text
    return p


def caption(text):
    return para(text, size=10.5, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)


def picture(name, width):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(3)
    p.add_run().add_picture(os.path.join(ASSETS, name), width=Inches(width))


def shade(cell, color):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def table(rows, widths, header=True, size=10.5):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.width = Inches(widths[j])
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            _fmt(p.add_run(str(val)), size, bold=(header and i == 0))
            if header and i == 0:
                shade(c, "D9E2F3")
    for i, row in enumerate(t.rows):          # keep each table on one page
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        if i < len(t.rows) - 1:
            for c in row.cells:
                for pp in c.paragraphs:
                    pp.paragraph_format.keep_with_next = True
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


pc = lambda x: f"{x*100:.1f}%"

# ================================================================ 1. Abstract
heading("1. Abstract")
para("Documentation is the part of software work that developers most often skip, and automatic documentation tools "
     "usually make it worse by describing code only from function signatures, producing comments such as "
     "\u201cgets the user\u201d. This project presents ChangeScribe, a deployable tool that documents a project from its "
     "history instead of its syntax. ChangeScribe reads the commits and merged pull requests of a sprint, including the "
     "review discussion, through the GitHub REST API or a local git clone. A parser removes noise such as merge and "
     "work-in-progress commits, classifies every change as a feature, fix, performance gain, refactor, documentation, test, "
     "build or breaking change, and extracts the sentences that explain why the change was made. A large language model "
     "then rewrites each change as a plain-English changelog line with a short impact statement, and an offline rule-based "
     "writer takes over when no API key is available. The result is written idempotently into CHANGELOG.md and a managed "
     "README block. The tool ships as a command line program, Flask web application, Docker image and reusable GitHub Action, "
     f"and is covered by 24 automated tests. On a labelled 40-commit sprint the offline writer removed all noise commits and "
     f"classified {pc(M['classification_accuracy'])} of genuine changes correctly.")

# ================================================================ 2. Introduction
heading("2. Introduction")
sub("2.1 Background of the topic")
para("Version control systems record every change a team makes, together with a message from its author and, on platforms such "
     "as GitHub, a pull request in which colleagues discuss the change. This history is a detailed account of how a product "
     "evolved, yet most readers never see it because it is scattered over hundreds of entries. Projects therefore maintain a "
     "changelog and README by hand, and these files are frequently out of date. Existing automatic generators either read "
     "source code structure, which says what a function is called but not why it exists, or require every commit to follow a "
     "strict format.")
sub("2.2 Need or motivation for choosing the project")
para("The motivation is practical: developers dislike writing documentation, and the knowledge needed to write it already "
     "exists in the repository. Capturing intent at the moment of change, when the author explains the problem in a commit body "
     "or a reviewer asks a question, is more reliable than reconstructing it weeks later. Combining this temporal information "
     "with natural language generation saves developer time and gives users and integrators a readable account of what changed "
     "and what it means for them.")
sub("2.3 Brief description of the system")
para("ChangeScribe is a four-stage pipeline: collector, parser, summarizer and renderer. No model is trained; the contribution "
     "is the data pipeline and the prompt contract that lets a pre-trained language model write accurate summaries from "
     "structured evidence. The system has a command line interface, a web interface, a Docker image and a GitHub Action that "
     "can open a pull request with the updated changelog every sprint.")
sub("2.4 Scope of the project")
bullet("Input: commit messages, pull request titles, descriptions and comments, labels and changed file names from public or private GitHub repositories or a local clone.")
bullet("Output: Keep-a-Changelog style Markdown, an updated CHANGELOG.md, a managed \u201cRecent changes\u201d block in README.md, and JSON.")
bullet("Out of scope: generating API reference documentation from source code, translating the changelog, and fine-tuning a model. Full source files and diffs are not sent to the language model.")

# ================================================================ 3. Problem statement
heading("3. Problem Statement")
para("Developers rarely keep README files and changelogs current, and tools that automate the task by reading function "
     "signatures cannot explain the reason for a change. The problem is to build a system that monitors a repository\u2019s commit "
     "history and pull request discussions over a sprint, understands why changes were made, removes irrelevant entries, and "
     "automatically produces accurate, structured, human-readable documentation that can be published without manual rewriting "
     "and that works even when no paid language model is available.")

# ================================================================ 4. Objectives
heading("4. Objectives")
numbered(1, "Collect commits, merged pull requests and review discussion for a chosen time window from the GitHub API or a local repository.")
numbered(2, "Clean and classify the history automatically, filtering noise and extracting the rationale behind each change.")
numbered(3, "Generate concise, factual changelog entries with a language model, with a deterministic offline fallback so the pipeline never fails.")
numbered(4, "Update CHANGELOG.md and the README safely and repeatably, without duplicating sections on re-runs.")
numbered(5, "Package the work as a deployable product (CLI, web app, Docker, GitHub Action, CI) and verify it with automated tests and measurable accuracy metrics.")

# ================================================================ 5. Methodology
heading("5. Methodology / System Design")
sub("5.1 Approach")
para("The approach treats documentation as a data-engineering problem. Evidence about intent is gathered and cleaned first, "
     "and the language model is used only for what it does best, rewriting that evidence as fluent prose under strict rules.")
numbered(1, "**Collect.** For GitHub sources, the tool lists closed pull requests merged inside the window, then fetches changed files, "
            "issue comments and review comments for each. Commits that belong to a pull request are marked as covered so they are not "
            "reported twice, and remaining direct commits are added. Pagination, retries and rate-limit waits are handled. For local "
            "repositories, git log with numstat supplies messages and file statistics.")
numbered(2, "**Parse.** Each change is classified using, in order, a conventional-commit prefix, pull request labels, keyword rules, and finally file paths "
            "(for example a change touching only docs/ is documentation). Merge commits, WIP, fixup and similar noise are discarded. "
            "Sentences containing cues such as \u201cbecause\u201d, \u201cso that\u201d or \u201cpreviously\u201d are extracted from the body and discussion as the "
            "rationale; BREAKING CHANGE footers and issue references are captured. Changes are packed into chunks of about 6000 characters.")
numbered(3, "**Summarize.** Each chunk is sent as JSON to the Anthropic Messages API with a system prompt that demands one plain-English sentence "
            "per change, an impact sentence drawn only from the supplied facts, and a strict JSON reply. Malformed output, network errors or a missing "
            "key trigger a per-chunk fallback to the offline heuristic writer.")
numbered(4, "**Render.** Entries are grouped into Breaking Changes, Added, Fixed, Performance, Changed, Documentation, Tests, Build & CI and Maintenance. "
            "The changelog update replaces the section for the same version heading, and the README update replaces the text between "
            "start and end markers, so repeated runs are idempotent.")
sub("5.2 Architecture diagram")
picture("architecture.png", 6.3)
caption("Figure 1: ChangeScribe system architecture")
sub("5.3 Flowchart")
picture("flowchart.png", 3.9)
caption("Figure 2: Processing flowchart")
sub("5.4 Use case summary")
table([["Actor", "Use case", "Interface"],
       ["Developer", "Preview the changelog for the last sprint", "CLI (--dry-run)"],
       ["Developer / release manager", "Write CHANGELOG.md and README block for a release", "CLI (--changelog, --readme)"],
       ["Team", "Receive an automatic pull request with the changelog every week", "GitHub Action"],
       ["Stakeholder / support", "Enter owner/name and read a formatted summary", "Web application"]],
      [1.7, 3.3, 1.5])
sub("5.5 Tools and technologies used")
table([["Area", "Technology"],
       ["Language and runtime", "Python 3.9+ (standard library: argparse, subprocess, re, dataclasses, json)"],
       ["Data collection", "GitHub REST API v3 via the requests library; git log --numstat for local repositories"],
       ["Language model", "Anthropic Messages API (model configurable, default claude-sonnet-5-5); offline rule-based fallback"],
       ["Web interface", "Flask, Jinja2 template, gunicorn"],
       ["Testing and evaluation", "unittest / pytest (24 tests), matplotlib for charts"],
       ["Packaging and deployment", "Dockerfile, Procfile, render.yaml, GitHub Actions (CI, composite Action, scheduled workflow)"]],
      [1.9, 4.6])

# ================================================================ 6. Results
heading("6. Results Summary")
sub("6.1 Dataset description")
para(f"A reproducible labelled dataset was generated by scripts/make_demo_repo.py: a git repository representing a two-week sprint with "
     f"{M['commits_total']} commits. Thirty are genuine changes (10 written as conventional commits and 20 as free-form messages, "
     f"2 of them breaking changes) covering eight categories, and ten are noise (merge commits, WIP, fixup, typo and version-bump commits). "
     f"Every commit carries a ground-truth category, a noise flag and a flag showing whether its message contains a reason. "
     f"Important limitation: the dataset is small, synthetic and was written by the author, and the keyword rules were adjusted while looking at it, "
     f"so the figures below are optimistic and best read as a regression baseline, not a benchmark on real repositories.")
sub("6.2 Model assessment parameters")
bullet("Noise precision and recall: share of discarded commits that really were noise, and share of noise that was discarded.")
bullet("Classification accuracy, per-category precision, recall and F1, and macro F1 over categories that occur in the data.")
bullet("Rationale recall: share of changes whose message contains a reason for which the \u201cwhy\u201d text was captured, and the number of false positives.")
bullet("Compression and speed: commits in versus entries out, and pipeline time. The evaluated writer is the offline heuristic; the LLM writer was verified with a mocked API and was not scored here.")
sub("6.3 Screenshot of the front page")
picture("screenshot.png", 5.2)
caption("Figure 3: Web interface showing a generated changelog (rendered from the bundled demo repository)")
sub("6.4 Output of the model and visualisation")
table([["Metric", "Result"],
       ["Commits in raw history", M["commits_total"]],
       ["Noise commits removed (precision / recall)", f"{M['noise_precision']:.2f} / {M['noise_recall']:.2f}"],
       ["Changelog entries produced", M["entries_written"]],
       ["Category accuracy, all genuine changes", f"{pc(M['classification_accuracy'])} (26 of 30)"],
       [f"  conventional commits (n={M['n_conventional']})", pc(M["accuracy_conventional"])],
       [f"  free-form messages (n={M['n_freeform']})", pc(M["accuracy_freeform"])],
       ["Macro F1", f"{M['macro_f1']:.2f}"],
       ["Rationale recall / false positives", f"{pc(M['rationale_recall'])} / {M['rationale_false_positives']}"],
       ["Pipeline time on local repository", f"{M['collect_ms'] + M['process_ms']:.0f} ms"],
       ["Automated tests", "24 passing"]],
      [4.2, 2.3])
pcat = M["per_category"]
rows = [["Category", "Precision", "Recall", "F1", "Support"]]
for c in ["feature", "fix", "perf", "refactor", "docs", "test", "build", "breaking"]:
    v = pcat[c]
    rows.append([c, f"{v['precision']:.2f}", f"{v['recall']:.2f}", f"{v['f1']:.2f}", v["support"]])
table(rows, [1.8, 1.2, 1.2, 1.2, 1.1])
picture("chart_accuracy.png", 4.6)
caption("Figure 4: Accuracy by commit style and overall metrics")
picture("chart_per_category.png", 5.0)
caption("Figure 5: Per-category precision and recall")
picture("chart_reduction.png", 4.0)
caption("Figure 6: Reduction from raw history to changelog entries")
para("Conventional commits were classified perfectly because the prefix states the category. Errors occurred only in free-form messages "
     "whose wording gives no keyword, such as \u201cMake login page not explode on empty password\u201d (a fix) and \u201cShow upload progress bar\u201d "
     "(a feature); these are exactly the cases where the language model writer is expected to help, because it reads the stored reason. "
     "A baseline that simply prints the raw git log would keep all ten noise lines, group nothing and show no reasons. "
     "Because entries keep the original reason sentences, the output is longer in characters than the raw titles and bodies; the gain is "
     "structure and readability rather than shorter text.")

# ================================================================ 7. Conclusion
heading("7. Conclusion")
para("The project delivered a complete, deployable tool that turns commit and pull request history into a structured changelog and README "
     "update. It collects evidence from GitHub or a local clone, filters noise, classifies changes, captures the stated reason for each, and "
     "uses a language model, or an offline fallback, to write readable entries. Updates are idempotent, the tool is packaged as a CLI, web "
     "application, Docker image and GitHub Action, and 24 automated tests pass without network access. On the labelled sprint the offline "
     f"writer removed all noise and reached {pc(M['classification_accuracy'])} accuracy. Remaining limitations are that evaluation used a small "
     "synthetic dataset, the LLM writer has not yet been scored on real repositories, and entries are only as informative as the commit and "
     "pull request text. Future work includes evaluating on open-source projects, adding diff-aware context and supporting more providers.")

doc.save(OUT)
print("saved", OUT)
