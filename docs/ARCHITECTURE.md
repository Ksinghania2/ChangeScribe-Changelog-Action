# Architecture

| Stage | Module | Input | Output |
|---|---|---|---|
| Collect | `collector.py` | repo path or `owner/name`, time window | `List[Change]` |
| Parse | `parser.py` | raw changes | classified, de-noised, rationale-enriched changes; chunks |
| Summarize | `summarizer.py` | processed changes | `List[Entry]` (category, summary, impact, refs) |
| Render | `renderer.py` | entries | Markdown; CHANGELOG / README updates |

Extension points: implement `Summarizer.summarize` to add another LLM provider; add rules to
`parser.KEYWORDS` / `PATH_HINTS`; add a new output format in `renderer.py`.

LLM contract: input is a JSON list of `{id, category, scope, title, why, files, issues, breaking}`;
output must be a JSON array of `{category, summary, impact, refs, scope}`. Malformed output or HTTP
errors trigger a per-chunk fallback to the heuristic writer.
