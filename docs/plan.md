# Plan

> **TruApply**, from "true". Package and command: `truapply`.

## Goal

**More interviews for less of your time.** And it must never lie for you, never apply to the same job twice, and never get your accounts banned.

Success is measured in **interviews**, not applications sent. A tool that sends 50 bad applications a day is worse than one that sends 10 good ones.

### Why build it

Free tools today fall into two groups:

- **Some never submit.** You still open every form and fill it in yourself.
- **Others submit carelessly:** the same resume everywhere, no fact checks, LinkedIn only, or behind a paid plan.

Few handle Indian forms well, and none learn what you actually want.

TruApply's place:

- **India-first.** Company career pages, with Indian form fields (notice period, current CTC) handled properly.
- **You stay in control.** The Chrome extension fills each form in your own Chrome, and you press Submit. Auto-submit is off until you turn it on.
- **It learns from you.** Every answer, dismissal, 👍 / 👎, tailoring note and rule teaches it what you want (see [outcomes.md](outcomes.md)).

### Auto-submit

Changed. The first plan made you earn auto-submit: a review queue, then an offer after 20 approvals in a row with no edits. The review queue, approvals and trust count are gone. Auto-submit is now a plain setting (`auto_submit` in `profile.json`, Settings → Applying):

1. Off until you turn it on.
2. Sends only career-page jobs scoring at or above your chosen score (80 by default), and only when nothing on the form is left for you.
3. Never past a human check ("prove you're human"), and never the same job twice.
4. Turns itself off after 2 👎 in the last 10 auto-submitted applications.

The extension does the sending, in a tab you can see. A run never sends anything.

## Target numbers

What "good enough" means. Every number is measured, not guessed.

| What | Target | How it's measured |
|---|---|---|
| Forms that go through | **≥ 90 %** of attempts on supported sites | Not measured yet. The planned Insights page was never built. |
| Bad matches | **< 10 %** of applications | Your 👎 "bad match" clicks on the tracker |
| Your edits to its answers | **Falling** week over week | Not measured yet. It was planned as edits ÷ approvals, and approvals are gone. |
| Made-up facts in resumes or answers | **0** | Automatic resume checks, plus a hand review of 20 tailored resumes before each release |
| Duplicate applications | **0** | Duplicate test plus a database check |
| Scheduled runs that finish without crashing | **≥ 95 %** | Run logs on the Activity page |
| Claude calls per application | **≤ 6** on average, falling over time | Usage counter in the database (calls per day) |
| New user, from install to first run | **≤ 15 min** | Timed on a fresh macOS account |

## Scope

### v1 does

| Command | What it does |
|---|---|
| `truapply tracker` | Starts the local tracker app (`--open` opens it, `--port`, `--allow-host`). On first use it opens on **Set up**: 5 steps (resume, details, rights and pay, how it runs, Chrome extension), and every other page is locked until it's done. |
| `truapply setup` | The same setup in the terminal: reads your resume and asks the [setup questions](setup-questions.md) |
| `truapply doctor` | Checks the data folder, database, profile, resume build, Claude budget, Claude Code, Chrome, tracker page and schedule. Says how to fix anything broken. |
| `truapply tailor JOB.txt --company … --title …` | Previews your resume tailored to one job description, with every check and the changed lines |
| `truapply run` | One pass: find jobs, score them, tailor your resume for the best. Nothing is sent. `--limit`, `--no-search`, `--find-companies`, `--job`, `--score`, `--no-find`, `--only find\|score\|tailor` |
| `truapply add LINK` | Adds a company from a Greenhouse, Lever or Ashby job or careers link and checks it now and on every run |
| `truapply schedule` / `unschedule` | Runs it on its own every 3 hours (or `--every` minutes): macOS launchd, Windows Task Scheduler; prints a cron line on Linux |
| `truapply boards --new` | Prints the career boards you found that aren't in the shared list yet, ready to contribute |
| `truapply archive` | Finds new companies in the latest web archive (no AI); the tracker and weekly runs start it in the background |

The **Chrome extension** (`truapply/extension/`) fills applications in your own Chrome. From the tracker, **Open in my Chrome** opens a job and the extension fills it with the tailored resume and saved answers; you check it and press Submit. When the site confirms, the job becomes `applied`. On any other job page, the extension's toolbar icon adds the job and fills the form. See [extension.md](extension.md).

Job sources:

- **Career pages** (Greenhouse, Lever, Ashby): found, scored and tailored on every run. The built-in list has 693 boards.
- **Wellfound:** checked on every run and listed for you to apply on the site.
- **LinkedIn, Naukri, Indeed and other sites:** a job page you open yourself can be added from the extension. TruApply never searches or applies there on its own.

Job statuses: `new`, `skipped`, `scored`, `ready`, `dismissed`, `applied`, `closed`.

### v1 doesn't

| Left out | Why | What happens instead |
|---|---|---|
| Searching Workday, iCIMS, Taleo and other sites that need an account per company | Every company needs a separate account and password | Open the form yourself and click the extension's icon to fill it |
| Solving CAPTCHAs or email/SMS codes | Getting past them is deceptive and breaks site rules | You solve them in your own Chrome. Auto-submit stops before them. |
| Logging in to job sites | Risky for your accounts | The extension works in your own Chrome, with your own logins |
| Applying on LinkedIn | Dropped on 27 Oct 2026: LinkedIn's rules ban automation and could restrict your account | The extension can add a LinkedIn job you open; you apply yourself |
| Refreshing your Naukri profile | Dropped: it would mean acting on your Naukri account | — |
| Reading your email | Dropped on 28 Oct 2026: an inbox password can read all your mail, and the risk isn't worth it | You mark what happened yourself |
| Other AI services (such as Gemini) | Dropped: Claude Code is the only AI, so every call goes through one safe wrapper | — |
| A hosted or cloud version | It's meant to stay on your machine | — |

---

## Build phases

A phase is **done only when every must-pass box is ticked**. Nothing is submitted to a real employer during development or tests.

```mermaid
flowchart LR
  P0[0 Plan] --> P1[1 Foundation] --> P2[2 Career pages] --> P3[3 Tracker] --> P3c[3c Extension] --> P3d[3d Setup in the app]
  P3d --> P4[4 Background] --> P4b[4b More companies] --> P7[7 Release]
```

Phase 5 (logged-in sites) and phase 6 (email replies) were dropped.

### Phase 0 · Plan ✅
These docs.

### Phase 1 · Foundation ✅

**Builds**
- Repo tooling, set up first: `ruff`, `mypy --strict`, `pytest`, `pre-commit`, GitHub Actions, secret scanning, the no-comments check and the layer test (see [CONTRIBUTING.md](CONTRIBUTING.md))
- Package and CLI skeleton
- Database with schema versions and migrations
- The safe Claude Code wrapper
- Setup wizard and profile validation
- Resume pipeline for LaTeX and for every other format: tailor, check, build the PDF, store the changes

**Must pass**
- [x] `pre-commit run --all-files` is clean on macOS. CI on macOS and Linux runs once the repo is on GitHub.
- [x] The no-comments check fails on a planted comment; the layer test fails on a planted upward import
- [x] Unit tests: duplicate key, number check, LaTeX preamble check, page count, AI reply parsing, profile validation, migrations
- [x] The setup wizard, run end to end with a real resume (answers piped in), produces a valid `profile.json`
- [x] Tailoring for 5 real job descriptions: 5/5 compile, none longer than the original, and every change reviewed by hand with **0 made-up facts**
- [x] A fake skill planted in a tailored resume is caught, and the original is used
- [x] A Claude call with tools turned off can't read a file, even when the prompt asks it to

### Phase 2 · Career pages ✅

**Builds**
- The shared company list `truapply/sources/companies.csv` (seed of ≥ 100 companies)
- Readers for the Greenhouse, Lever and Ashby public APIs
- Board discovery by web search
- Title filter and AI scoring
- Detection of employer "no AI" rules
- The general form filler, plus a local multi-step test form. This Playwright filler was later replaced by the Chrome extension (phase 3c).

**Must pass**
- [x] 20 boards polled: 100 % of jobs have a title, company, location, link and description
- [x] Local test form (every field type, 3 steps): 10/10 submitted and detected as success
- [x] Dry run on 10 real Greenhouse/Lever/Ashby forms: ≥ 9 reach Submit with every required field filled (screenshots reviewed)
- [x] A job post with hidden instructions ("ignore your rules…") changes nothing: no tools used, answers still from the profile
- [x] A job post saying "no AI-generated applications" is skipped. A form box "I did not use AI" is never ticked.
- [x] The same job from two sources is applied to once
- [x] A removed job (API 404), or an Ashby job past its deadline to apply, is marked `closed`

### Phase 3 · Tracker page and learning from you ✅

**Builds**
- Application list with filters
- Resume change view, a "what was sent" view per application, and a button to go back to the original resume
- 👍 / 👎 buttons, dismiss reasons, and resume tailoring notes
- A "Tell TruApply" box for plain-language rules
- The "What it learned" page: suggestions, your rules, tailoring notes and saved answers, all editable
- A "Ready for you to apply" list (it replaced "Finish these"): **Open in my Chrome** opens the job, the extension fills it with the tailored resume and saved answers, and you do any human check and press Submit. TruApply never solves the check itself.

Changed: "Needs your answer", approvals, the trust counter and the auto-submit offer were dropped once the extension took over filling. Questions it can't answer are now left for you on the form itself, and auto-submit is a plain setting (see [Auto-submit](#auto-submit)). The planned count of human checks per site isn't built.

**Must pass**
- [x] Every status is visible and filterable
- [x] From "Ready for you to apply", the job opens filled in your own Chrome; submitting it, or **I submitted it**, sets `applied` (14 real applications sent this way, plus a browser test)
- [x] Answer a question on a form, and the next form with that question fills without an AI call
- [x] Edit a saved answer on "What it learned" → the next form with that question uses your version
- [x] Dismiss 3 jobs as "too senior" → a suggestion to add that title word to "skip titles" appears, and nothing changes until you accept it
- [x] A rule typed in "Tell TruApply" ("no staffing agencies") changes the next scores, appears on "What it learned", and can be deleted there
- [x] A tailoring note ("don't change my headline") is followed in the next 5 tailored resumes
- [x] Two 👎 in the last 10 auto-submitted → auto-submit turns off
- [x] The change view shows exactly the changed lines for 5 tailored resumes
- [x] A POST from another website is rejected (curl test with a fake `Origin`)
- [x] Checked in a real browser, with a screenshot
- Dropped with the review queue: picture check after Submit → "Finish these"; approve → sent on the next run with `--send`; the auto-submit offer after 20 clean approvals.

### Phase 3b · React tracker ✅

**Builds**
- The tracker as a React + TypeScript app (`web/`, built with Vite and shipped prebuilt inside the package, so users don't need Node), talking to the Python tracker only through the JSON API in [tracker-api.md](tracker-api.md)
- Pages: Today, Jobs, All jobs, Companies, Activity (runs and their logs), Learned, Settings, and a page per job
- Inline answer editing, live run progress without reloads
- The tracker choosing a free port when 8765 is taken
- A workflow map page (`/workflow`), removed on 2026-10-29: Today's pipeline counts (Found, Not a fit, Good matches, Ready for you, Applied) replace it

**Must pass**
- [x] Every page of the tracker works in the React app, with the same safety checks (Host, Origin, JSON-only POST, strict CSP with only the tracker's own scripts)
- [x] The workflow map's counts matched the Jobs page for every box (before it was removed)
- [x] Checked in a real browser, light and dark, with screenshots of every page; a browser test also checks phone width has no sideways scrolling (a phone layout isn't needed for now)

### Phase 3c · Chrome extension ✅

It replaced the Playwright form filler and the separate filled-in browser. See [extension.md](extension.md).

**Builds**
- The extension in `truapply/extension/`, loaded from a folder. It talks only to the app on `127.0.0.1`.
- Filling in your own Chrome: saved answers and profile facts first, then Claude for the rest. Consent boxes and legal questions it can't answer are left for you, outlined.
- **Open in my Chrome** from the tracker, and the toolbar icon to add and fill a job on any other page. A LinkedIn job page can only be added.
- The site's confirmation marks the job `applied`, and what you typed is learned.
- Auto-submit, as a setting (see [Auto-submit](#auto-submit)), with **Send these with auto-submit** on Today.

**Must pass**
- [x] Requests from other websites and extensions are refused
- [x] Saved answers fill without an AI call; consent is never answered and is left for you
- [x] Submitting marks the job applied; doing it twice changes nothing; a thank-you page on its own address also counts (browser test)
- [x] Auto-submit sends nothing while off or during a run, sends only strong jobs one at a time, and holds a stalled send for you without trying it again
- Live tests (`pytest -m network`, `tests/live/test_extension_live.py`) fill real application forms with real Claude answers, leave consent to you, and submit nothing.

### Phase 3d · Setup in the tracker app ✅

**Builds**
- First-run setup in the app, in 5 steps: your resume (Claude reads it), your details and jobs to look for, rights and pay (never filled in for you), how it runs, and the Chrome extension with a live installed check
- Every other page is locked until setup is done; the rest take defaults (see [setup-questions.md](setup-questions.md))

**Must pass**
- [x] A fresh folder asks for setup and can't run
- [x] A wrong file is refused before Claude reads it; finishing needs the resume first
- [x] Work rights are never filled in for you
- [x] Finishing saves the profile and opens the app; picking a schedule turns automatic runs on

### Phase 4 · Background runs and daily summary

**Builds**
- `schedule` / `unschedule` (macOS launchd and Windows Task Scheduler; a cron line on Linux), and turning automatic runs on or off from the tracker
- A run lock, daily limits and pauses
- Crash recovery and a daily Claude call budget
- Daily summary and notifications
- `doctor`

**Must pass**
- [ ] After `schedule`, a run starts on its own and writes the log
- [x] A second run started during a first exits with "already running"
- [x] The daily limit and the LinkedIn limit stop getting jobs ready at exactly the limit
- [x] The summary notification shows once a day
- [x] `doctor` names each broken piece and its fix (tested by breaking each one)
- Changed: "a run killed right after clicking Submit is marked `unconfirmed`". Runs no longer submit. Auto-submit marks a job before pressing Submit, so it's never sent twice.

### Phase 4b · More companies

Most Indian startups don't use Greenhouse, Lever or Ashby. A check of 975 Bengaluru startups' careers pages found Keka on 41, Google Forms on 30, Darwinbox on 27, Greenhouse, Lever and Ashby together on 28, Wellfound on 17, Zoho Recruit on 15 and Workday on 14; the rest load their links with JavaScript or post only on job sites. The measure is **relevant open jobs found per week**. In order, each its own change:

1. **Companies from the web archive.** The free Common Crawl index lists every Greenhouse, Lever and Ashby page it has visited. A partial read on 28 Oct 2026 gave 2,353 names we didn't have, 210 of them with jobs in India. Read in the background beside runs, once a week or from **Search the web archive**; only new names are checked, and no AI is used.
2. **Companies by name.** Paste company names or websites on the Companies page; each is tried on Greenhouse, Lever and Ashby, and kept only when it has jobs in your country, so a same-named company abroad isn't added.
3. **Companies from every job.** Any job whose apply link or description points to a Greenhouse, Lever or Ashby board adds that company.
4. **Many small web searches.** One search per role, place and job system instead of one per job system, within the daily Claude budget.
5. **Keka and Darwinbox.** Only if their job lists can be read without signing in. Then Zoho Recruit.

SmartRecruiters and Workday stay out (dropped on 28 Oct 2026).

**Must pass**
- [x] The built-in list has the 17 Bengaluru companies found on Greenhouse, Lever and Ashby
- [x] The web archive adds companies with jobs in your country, reads each crawl once, retries pages that time out, and checks a name again only after 180 days
- [x] Pasting a name that matches a board with jobs in your country adds it; one with jobs only abroad is not added
- [ ] A Wellfound or pasted job linking to a Greenhouse, Lever or Ashby board adds that company
- [ ] The weekly web search finds more new companies than before, and stays within the daily Claude budget
- [ ] Keka and Darwinbox: a read-only test shows whether jobs can be listed without signing in

### Phase 5 · Logged-in sites

**Dropped.** The plan was to search and apply on LinkedIn, Naukri, Indeed and Wellfound with your saved logins. TruApply never logs in to job sites now:

- **LinkedIn:** auto-apply dropped on 27 Oct 2026, because LinkedIn's rules ban automation and could restrict your account. The extension can add a LinkedIn job you open; you apply yourself.
- **Naukri and Indeed:** not searched. A job page you open can be added from the extension.
- **Wellfound:** read on every run without logging in, and listed for you to apply on the site.

### Phase 6 · Replies and learning from results

**Dropped on 28 Oct 2026.** Reading your inbox needs a password that can read all your mail, so TruApply never connects to email.

### Phase 7 · Open-source release

**Builds**
- [x] README (install, disclaimer), MIT LICENSE, CONTRIBUTING
- [ ] Issue and PR templates, CHANGELOG
- [x] Shared company list of ≥ 300 companies (693 boards)
- [ ] Version `0.1.0` (now `0.1.0.dev0`)

**Must pass**
- [ ] Fresh macOS user account: README install → first run in ≤ 15 min
- [ ] Fresh Linux machine: the same
- [ ] Fresh Windows machine: the same
- [x] Secret scan of the full git history is clean, and there's no personal data in the repo (search for the owner's name, email and phone)
- [ ] Every target number is met, or listed as a known gap in the release notes
- [x] Pushed to GitHub only after the owner says so (private repo)

---

## Open questions

| Question | Current answer |
|---|---|
| Name | **Decided: TruApply** (renamed from SatyaApply on 28 Oct 2026). Not yet checked: whether `truapply` is free on PyPI, npm and GitHub (organization), and `truapply.com`. Check and claim them before announcing. |
| License | MIT |
| Claude subscription inside a public tool | Each user runs their own Claude Code with their own login. Check Anthropic's terms before release. `ANTHROPIC_API_KEY` also works with no code change. |
