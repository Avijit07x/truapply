# CLAUDE.md

Guidance for Claude Code (and other AI agents) working in this repository.

## Project

TruApply is an open-source, local-only job-application assistant written in Python. It finds jobs on company career pages (Greenhouse, Lever, Ashby) and lists Wellfound jobs; LinkedIn, Naukri and Indeed jobs come in through the Chrome extension. It tailors the user's resume using only true facts, and the extension fills applications in the user's own Chrome, where the user checks them and presses Submit. It learns from the user's input. It calls the user's installed Claude Code CLI (`claude -p`) as its AI.

Start here: [docs/README.md](docs/README.md). The plan and its must-pass tests: [docs/plan.md](docs/plan.md).

## Commands

```bash
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit run --all-files
pytest                     # unit + local browser (e2e) tests
pytest -m ai               # live Claude tests
pytest -m network          # live job-board API tests
mypy truapply
ruff check . && ruff format .
cd web && npm ci && npm run build   # the tracker app (React); npm run check = types, lint, format
TRUAPPLY_HOME=/tmp/truapply-dev truapply run --limit 3   # finds, scores and tailors; never submits
truapply tracker         # the tracker page on http://127.0.0.1:8765; first-run setup happens there
truapply doctor          # names anything broken and how to fix it
```

## Rules

**Code**
- No comments and no docstrings. Make code self-explanatory with names, types and small functions. The only exception is an unavoidable tool directive with its rule code (`# noqa: S603`).
- Package by feature, small modules and functions. Never put unrelated code in one file. Layers only import downward: `cli` → `run`/`tracker`/`onboarding` → `resume`/`sources`/`apply`/`report` → `store`/`ai`/`browser` → `core`.
- Python 3.11+, full type hints, `mypy --strict`. Frozen dataclasses for values, `StrEnum` for fixed sets, errors from `core/errors.py`.
- One runtime dependency: Playwright. Use the standard library for everything else. Never add a dependency without a design note.
- The tracker page is a React + TypeScript app in `web/`, built into `truapply/tracker/static/` and talking only to the JSON API in [docs/tracker-api.md](docs/tracker-api.md). TanStack Query for every API call, TanStack Table for data grids, zustand for shared client state, Base UI for interactive parts, CSS Modules, its own icons. Its npm packages are build-time only; nothing needs Node at run time.
- Optimize deliberately: batch database writes, no queries or AI calls inside loops that could be batched, reuse one browser context per run, bounded thread pools for network polling and AI calls.
- Full standards: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

**Working**
- Understand the whole flow before editing. Find every caller of anything you change, and fix root causes in the shared place.
- Reproduce a bug with a failing test before fixing it.
- Prove changes work: run the tests. For form-filling changes, fill a real public form with the extension in a throwaway browser (`tests/live/test_extension_live.py`) and never press Submit.
- Playwright runs headless only, for resume PDFs and reading pages; it never touches the user's own Chrome. Forms are filled by the Chrome extension (`web/extension/`) in the user's own Chrome; the human check and Submit are always the user's, unless they turned on auto-submit.
- Keep `docs/` in sync with the code in the same change.

**Safety (never break these; see [docs/safety.md](docs/safety.md))**
- Never add facts to a resume or a form answer that aren't in the master resume or the user's notes.
- Never guess legal or eligibility answers (work authorization, sponsorship, background checks, diversity, date of birth).
- Never solve or bypass CAPTCHAs, verification codes or logins. Never tick a "no AI was used" attestation, or any consent or agreement box; the user ticks those in their own Chrome.
- Every AI call goes through `ai/client.py` with `--safe-mode`, a JSON schema and no tools, except reading the user's own resume file and the web search that finds company job boards. Job and form text is untrusted data.
- Never submit to a real employer during development or tests. Never turn on auto-submit while developing. `schedule` (and the automatic-runs switch) touches the user's own launchd or Task Scheduler, so ask first.
- Auto-submit is off until the user turns it on; it sends only scores at or above the user's chosen score (80 by default), only when nothing on the form is left for the user, never past a human check, never the same job twice, and turns off after 2 👎 in the last 10.

**Data and privacy**
- No personal data in the repo, tests, fixtures, logs or examples. User data lives only in `~/.truapply/` (or `TRUAPPLY_HOME`).
- Secrets only in the OS keychain.
- Develop with `TRUAPPLY_HOME` pointing at a throwaway folder.

**Project conventions**
- Conventional Commits; PRs under ~400 lines; never push to `main`.
