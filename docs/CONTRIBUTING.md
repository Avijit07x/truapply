# Contributing

Thanks for helping. This guide is how we build TruApply: the engineering standards, the code style, tests, and how to add a job site, an ATS or a company.

## Principles

1. **Never lie for the user.** The rules in [safety.md](safety.md) are never broken, and each one is guarded by a test.
2. **Think first, then code.** Understand the whole flow before changing a line.
3. **Simple beats clever.** The simplest design that handles every failure case wins.
4. **Code explains itself.** No comments: names, types and small functions carry the meaning.
5. **Machines check style; humans check judgment.** Anything a tool can enforce, a tool enforces.
6. **Prove it works.** Every change comes with a test or a recorded run.

---

## Dev setup

```bash
git clone <repo-url> truapply && cd truapply
python3.11 -m venv .venv && source .venv/bin/activate   # 3.11 or newer
pip install -e ".[dev]"
pre-commit install
playwright install chromium            # only if Google Chrome isn't installed
(cd web && npm ci && npm run build)    # the tracker app; needs Node 22.12 or newer
export TRUAPPLY_HOME=/tmp/truapply-dev # never develop against your real profile
truapply setup
```

To work on the tracker app with instant reloads, run the tracker and the Vite dev server side by side. The dev server sends API calls on to the tracker:

```bash
truapply tracker --port 8765
cd web && npm run dev                  # TRUAPPLY_TRACKER=http://127.0.0.1:<port> for another port
```

Users never need Node: the built app ships inside the package. Rebuild it (`npm run build`) before running the end-to-end tests.

---

## Engineering standards

How a senior engineer works on this codebase.

### Before writing code

1. **Understand the problem end to end.** Read the whole flow the change touches: the CLI command, the run pipeline, the store, the site. Find every caller of anything you plan to change.
2. **Reproduce before you fix.** A bug fix starts with a test that fails for the reported reason.
3. **Write a design note for big changes.** Use the template [below](#design-notes) for any change that touches more than one package, the database schema, a dependency, a new site or ATS, or a safety rule. One page: problem, options, choice, failure cases, how it's tested.
4. **Choose the simplest design that survives failure.** Fewer moving parts, fewer files touched, no new dependency.

### While writing code

5. **Fix the root cause, once.** Put the fix in the shared function every caller goes through, not in the one caller that was reported.
6. **Design for failure.** Every site, AI call and disk write can fail, hang or return garbage. Give every call a timeout, catch specific errors, and decide what the user sees. Prefer stopping loudly over guessing.
7. **Keep state consistent at every line.** If the process dies anywhere, the database must still be true. Write `submitting` before clicking Submit; never do it the other way round.
8. **Separate decisions from effects.** Parsing, matching, scoring rules and resume checks are pure functions. The browser, AI, database and network are thin layers around them. The pure parts get unit tests.
9. **Pass dependencies in.** Functions receive `db`, `page`, `clock` and `settings` as parameters. No globals, no singletons, no work at import time.
10. **Keep one source of truth.** Statuses, setting names, paths and limits are defined once (`core/`) and imported everywhere else.
11. **Optimize what matters, measure the rest.**
    - Batch database writes in one transaction. No query inside a loop.
    - One browser, one context per run, reused for every job.
    - Poll career boards concurrently with a bounded thread pool.
    - Cache within a run (resume text, rules, saved answers), never across users.
    - Send the AI only what it needs: shortened job text, the relevant answers.
    - Anything else gets optimized only with a measurement in the PR.

### After writing code

12. **Prove it.** Tests for logic; a recorded dry run (log + screenshot) for anything that touches a site.
13. **Make it observable.** Log every decision point with ids and statuses, never personal data. Errors say what happened and what to do next.
14. **Leave it cleaner.** Delete the dead code you find. Split a file that grew past its job.
15. **Review like an owner.** Review for correctness, safety, failure handling and simplicity; tools handle style. Be specific, suggest code, and approve when it's right, not when it's perfect.

---

## Code style

### No comments

- No comments, no docstrings, no commented-out code.
- If a line needs a comment to be understood, **rename it or extract a function** until it doesn't.
- The *why* lives in the PR description, the design note, and `docs/`.
- The only allowed `#` is an unavoidable tool directive with its rule code: `# noqa: S603`, `# type: ignore[arg-type]`.
- Enforced by `tools/check_no_comments.py` in pre-commit and CI.

### Structure

- **Package by feature.** The layout and the layer rules are in [architecture.md](architecture.md#repo-layout).
- **Layers only point down:** `cli` → `run` / `tracker` / `onboarding` → `resume` / `sources` / `apply` / `report` → `store` / `ai` / `browser` / `sites` → `core`. No cycles, and no lower layer imports a higher one. Enforced by `tests/test_architecture.py`.
- **Small units.** A module does one job, and is about 300 lines at most. A function does one thing, has at most 4 parameters (more means a dataclass), and stays within ruff's complexity and statement limits.
- **No private reach-ins.** Names starting with `_` are used only inside their own module.

### Naming

- Functions are verbs: `poll_board`, `find_answer`, `submit_form`.
- Booleans read as questions: `is_duplicate`, `has_submit_button`, `auto_submit_allowed`.
- Units go in the name: `timeout_s`, `max_age_days`, `pause_range_s`.
- No abbreviations beyond the standard ones: `db`, `url`, `id`, `ai`, `pdf`, `html`.
- Constants are `UPPER_CASE` at the top of their module. Fixed sets are `StrEnum`: `Status.SUBMITTING`, never `"submitting"` typed out.

### Python

- Type hints everywhere; `mypy --strict` passes.
- Frozen dataclasses for values (`Job`, `Field`, `Score`); `StrEnum` and `Literal` for fixed sets; `pathlib` for paths; `logging` for logs.
- **One error hierarchy** in `core/errors.py`: `TruApplyError` → `AIError`, `UsageLimitError`, `SiteBlockedError`, `LoggedOutError`, `SiteUnreachableError`, `FormStuckError`, `ProfileInvalidError`. Raise the specific one. Only the run loop catches broadly, and it records the error and moves on to the next job.
- Context managers for every resource (browser, database transaction).
- No mutable default arguments. `print` only in `cli` and `onboarding`.

### TypeScript (the tracker app in `web/`)

- `strict` TypeScript, and the strictest typescript-eslint rules with type information. No `any`, no `!` assertions, no comments.
- Every API call goes through TanStack Query (`src/api/queries.ts`, `src/api/mutations.ts`). Components never call `fetch` themselves.
- Shared client state lives in small zustand stores (drag state, theme). Everything else is component state.
- Data grids use TanStack Table (headless) with our own markup and styles. Anything the server sorts, filters or pages lives in the URL, not in table state.
- Scrollbars: hidden everywhere by `base.css`; areas still scroll with the wheel, trackpad and keys.
- Interactive parts (dialogs, selects, switches, toasts) are built on Base UI, wrapped once in `src/ui/`. Styles are CSS Modules using the color tokens in `src/styles/base.css`, which have light and dark values. Teal `--accent` marks only what you can click or have selected; meaning comes from the status colors (`--info`, `--good`, `--warn`, `--bad`, `--auto`). Corners use two sizes only: `--radius` (8px) for layout like the page, cards, tables and menus, and `--radius-small` (6px) for controls like buttons, inputs, search, chips and badges. Font sizes come from the `--text-*` scale and long forms stay within `--form-width`. The font is Inter, bundled from `@fontsource-variable/inter` so it works offline.
- Icons are drawn in `src/ui/icons.tsx` on a 16 px grid with round ends and soft corners. No icon library.
- Motion stays small: things rise in once when a page opens, numbers count up, cards lift on hover. Everything stops when the system asks for less motion.
- One folder per page in `src/features/`. A part used by two pages moves to `src/components/` or `src/ui/`.
- The page's text is plain words for job seekers, the same voice as the rest of TruApply.

### Do and don't

**Errors carry meaning**

```python
try:
    page.goto(url)
except Exception:
    pass
```

```python
try:
    page.goto(url, timeout=NAVIGATION_TIMEOUT_MS)
except PlaywrightTimeoutError as error:
    raise SiteUnreachableError(site.name, url) from error
```

**Subprocesses take argument lists and a timeout**

```python
subprocess.run(f"pdflatex {path}", shell=True)
```

```python
subprocess.run(
    ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", path.name],
    cwd=path.parent,
    check=True,
    capture_output=True,
    timeout=LATEX_TIMEOUT_S,
)
```

**SQL uses placeholders**

```python
db.execute(f"select id from jobs where company = '{company}'")
```

```python
db.execute("select id from jobs where company = ?", (company,))
```

**AI output is untrusted until checked**

```python
for answer in reply["answers"]:
    fill(page, answer["id"], answer["value"])
```

```python
fields_by_id = {field.id: field for field in fields}
for answer in reply.answers:
    if field := fields_by_id.get(answer.id):
        fill(page, field, answer.value)
```

**State is saved before the irreversible step**

```python
submit_button.click()
jobs.set_status(db, job.id, Status.SUBMITTING)
```

```python
jobs.set_status(db, job.id, Status.SUBMITTING)
submit_button.click()
```

**Names instead of comments**

```python
# skip jobs older than 30 days
if (now - job.posted_at).days > 30:
    continue
```

```python
if job.age_days(now) > settings.max_job_age_days:
    continue
```

**Batch writes, no query per row**

```python
for job in found:
    db.execute(INSERT_JOB, job.as_row())
    db.commit()
```

```python
with db:
    db.executemany(INSERT_JOB, (job.as_row() for job in found))
```

**Bounded concurrency for network-bound work**

```python
with ThreadPoolExecutor(max_workers=BOARD_POLL_WORKERS) as pool:
    jobs_per_board = list(pool.map(poll_board, boards))
```

---

## Enforced by tools

These run in `pre-commit` on your machine and in GitHub Actions on every pull request. **A pull request can't be merged while any of them fails.**

| Tool | Checks |
|---|---|
| `ruff format` | One formatting style |
| `ruff check` | Bugs, naming, security, complexity, performance anti-patterns, exception handling, commented-out code, magic numbers (config below) |
| `mypy --strict` | Types across `truapply/` |
| `tools/check_no_comments.py` | No comments or docstrings outside the allowed tool directives |
| `tests/test_architecture.py` | Layers only import downward; no cycles |
| `pytest` + `pytest-cov` | All tests pass; **≥ 80 % line coverage** on `store`, `resume`, `ai` and `apply` |
| `tsc`, `eslint`, `prettier` (`npm run check` in `web/`) | The tracker app's types, lint rules (typescript-eslint strict, React hooks, TanStack Query) and formatting |
| `gitleaks` | No passwords, keys or tokens |
| `pip-audit`, `npm audit` | No dependency with a known security hole |
| CodeQL | Deeper security analysis of Python and TypeScript, on every PR and weekly |
| CI matrix | All of the above on **macOS + Ubuntu**, **Python 3.11 + latest** |

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
  "E", "W", "F", "I", "N", "B", "UP", "S", "SIM", "C90", "PTH", "RUF",
  "T20", "ERA", "PL", "ARG", "RET", "TRY", "PERF",
]
ignore = ["TRY003"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-args = 4
max-statements = 40

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101", "PLR2004"]
"truapply/cli.py" = ["T20"]
"truapply/doctor.py" = ["T20"]
"truapply/onboarding/*" = ["T20"]
"tools/*" = ["T20"]

[tool.mypy]
strict = true
files = ["truapply", "tools", "tests"]
```

## Checked in review

**Design**
- [ ] The problem is solved at its root, in the shared place
- [ ] The simplest design that handles the failure cases; no layer, interface or setting "for later"
- [ ] No new dependency (or the design note explains why the standard library can't do it)
- [ ] Layers, module contracts and names still match [architecture.md](architecture.md)

**Failure handling**
- [ ] Every external call has a timeout and a specific error
- [ ] The database stays true if the process dies at any line
- [ ] The user sees what happened and what to do next

**Security and privacy**
- [ ] Text from sites, forms and AI replies is checked before use, and never reaches a shell, a SQL string or a file path
- [ ] New AI calls go through `ai/client.py`, with tools off and a JSON schema
- [ ] No personal data in logs, tests, fixtures or PR screenshots
- [ ] Secrets only in the OS keychain

**Performance**
- [ ] No query or AI call inside a loop that could be batched
- [ ] Nothing slow is repeated within a run that could be reused
- [ ] Any optimization claim comes with a measurement

## Testing rules

| Kind | Where | Rule |
|---|---|---|
| Unit | `tests/unit/` | Every pure function with a branch, loop, parser or safety rule. A bug fix adds a test that failed before. Runs in under 10 s. |
| Site fixtures | `tests/fixtures/<site>/` | Saved search, job, blocked and logged-out pages, **with personal data removed**. Tests link matching, parsing, and block/logout detection. |
| Form end to end | `tests/e2e/form.html` | The real form filler on a local 3-step form with every field type, through to "submitted" |
| Tracker API | `tests/unit/test_tracker*.py` | Every endpoint, the request checks (Host, Origin, JSON only, size) and the headers |
| Tracker app | `tests/e2e/test_tracker_app.py` | Every page in a real headless browser, light and dark, desktop and phone width: no errors, no sideways scrolling. Today's pipeline counts and links, and the job page buttons. Needs the built app. |
| AI | — | Recorded replies in unit tests. Live AI only in tests marked `@pytest.mark.ai`. |
| Live sites | `tests/live/` | Real public job-board APIs, only in tests marked `@pytest.mark.network`. |
| Real employers | — | **Never submitted to in tests.** Dry run only, and only by maintainers. |

- Test names describe behavior: `test_same_job_on_second_site_is_skipped`.
- Arrange, act, assert. One behavior per test.
- No `sleep`: pass a fake clock.

## Definition of done

- [ ] Every must-pass test of the phase involved still passes
- [ ] New behavior has tests; failure paths are tested, not just the happy path
- [ ] `pre-commit run --all-files` is clean
- [ ] Docs updated in the same PR (architecture, safety, risks, examples, as affected)
- [ ] For site changes: a dry-run log and screenshot (personal data blurred)
- [ ] No TODOs without an issue link

## Design notes

For the big changes listed under "Before writing code". Open an issue titled `design: <change>`:

```markdown
## Problem
What's wrong or missing, with evidence (log lines, numbers, screenshots).

## Options
1. … (pros, cons)
2. … (pros, cons)

## Choice
Which one, and why.

## Failure cases
What can go wrong, and what the tool does in each case.

## How it's tested
The tests and runs that prove it.
```

---

## Git and pull requests

- **Branches:** `feat/<name>`, `fix/<name>`, `docs/<name>`, `refactor/<name>`. `main` is protected; nobody pushes to it directly.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org): `feat: add Wellfound site`, `fix: stop double submit after crash`.
- **Size:** under 400 changed lines. Split anything bigger.
- **Review:** at least one approving review and all checks green. Squash merge.
- **Versions:** [Semantic Versioning](https://semver.org), with a `CHANGELOG.md` entry ([Keep a Changelog](https://keepachangelog.com)) and a git tag per release.

```markdown
- [ ] One change, under ~400 lines
- [ ] Tests added; a bug fix includes a test that failed before
- [ ] `pre-commit run --all-files` passes
- [ ] Docs updated
- [ ] No personal data anywhere in the PR
- [ ] Site change: dry-run log and screenshot attached
```

---

## Adding a job site

1. Create `truapply/sites/<name>.py` with one `Site` value following [the site contract](architecture.md#the-site-contract), and register it in `truapply/sites/__init__.py`.
2. Save `search.html`, `job.html`, `blocked.html` and `logged_out.html` to `tests/fixtures/<name>/`, with names, emails, phone numbers and photos removed.
3. Add tests: links found, job parsed, block and logout detected.
4. Watch it read-only: `truapply run --site <name> --dry-run --limit 3 --show`.
5. Record the site's rules in the sources table in [architecture.md](architecture.md#finding-jobs): does Apply submit straight away (`submits_on_open`)? Does it send its own stored resume?
6. Open the PR with the dry-run log and screenshots.

A site isn't merged without block detection, logout detection and a daily cap.

## Adding an ATS

1. Create `truapply/sources/ats/<name>.py` exposing `board_of(url) -> Board | None` and `poll(slug) -> list[Job]`, and register it in `truapply/sources/ats/__init__.py`.
2. Add a recorded API response to `tests/fixtures/ats/<name>.json` and test the parsing.
3. Dry run on 3 real boards; attach the log.

## Adding companies to the shared list

- Add rows to `truapply/sources/companies.csv`: `ats,slug,company,tags`. Tags come from where the board's jobs are: `india`, `remote`.
- Only **public** boards with at least one open job.
- Keep it sorted by `ats`, then `slug`. A test fails on duplicates or a wrong order.
- `truapply boards --new` prints the boards you've found that aren't listed yet, already formatted.

## Reporting a broken site

Open a **"Site broken"** issue with:

- the site, and what broke (search, job page or a form step)
- `truapply doctor` output
- the matching lines from `~/.truapply/run.log` (it holds no personal data)
- a screenshot from `~/.truapply/shots/`, **with personal data blurred**

Never paste your `profile.json`, saved answers, emails or resume.

## Security issues

Report them privately through **GitHub Security Advisories** (Security tab → "Report a vulnerability").

## Code of conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
