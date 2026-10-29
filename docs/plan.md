# Plan

> **TruApply**, from "true". Package and command: `truapply`.

## Goal

**More interviews for less of your time.** And it must never lie for you, never apply to the same job twice, and never get your accounts banned.

Success is measured in **interviews**, not applications sent. A tool that sends 50 bad applications a day is worse than one that sends 10 good ones.

### Why build it

Free tools today fall into two groups:

- **Some never submit.** You still open every form and click Submit yourself.
- **Others submit carelessly:** the same resume everywhere, no fact checks, LinkedIn only, or behind a paid plan.

None of them handle Naukri well, and none learn what actually leads to interviews.

TruApply's place:

- **India-first.** Naukri, LinkedIn and company career pages, with Indian form fields (notice period, current CTC) handled properly.
- **Auto-submit you can trust.** It starts by asking you to approve each application, and offers auto-submit only once it has earned that trust.
- **It learns from you.** Every answer, approval, dismissal, edit and rule teaches it what you want (see [outcomes.md](outcomes.md)).

### Trust before auto-submit

1. Everyone starts in the **review queue**, the project owner included. TruApply fills each application, and you approve it on the tracker page.
2. After **20 approvals in a row with no edits**, it offers to turn on auto-submit for strong matches (score 80 or more). You decide.
3. An edit or a 👎 "bad match" resets the count.
4. Once auto-submit is on, if 2 of the last 10 auto-submitted applications get a 👎, it switches back to the review queue and tells you.

## Target numbers

What "good enough" means. Every number is measured, not guessed.

| What | Target | How it's measured |
|---|---|---|
| Forms that go through | **≥ 90 %** of attempts on supported sites | Insights page: last 50 attempts per site |
| Bad matches | **< 10 %** of applications | Your 👎 "bad match" clicks on the tracker |
| Your edits per reviewed application | **Falling** week over week | Tracker: edits ÷ reviews. This proves it learns from your input. |
| Made-up facts in resumes or answers | **0** | Automatic resume checks, plus a hand review of 20 tailored resumes before each release |
| Duplicate applications | **0** | Duplicate test plus a database check |
| Scheduled runs that finish without crashing | **≥ 95 %** | Run log |
| Claude calls per application | **≤ 6** on average, falling over time | Usage counter in the database |
| New user, from install to first dry run | **≤ 15 min** | Timed on a fresh macOS account |

## Scope

### v1 does

| Command | What it does |
|---|---|
| `truapply setup` | Reads your resume, asks the [setup questions](setup-questions.md), and saves your profile |
| `truapply login` | Opens Chrome so you can log in to LinkedIn, Naukri, Indeed and Wellfound once |
| `truapply doctor` | Checks that everything works: Claude, Chrome, LaTeX, each login, schedule. Says how to fix anything broken. |
| `truapply tailor JOB.txt --company … --title …` | Previews your resume tailored to one job description, with every check and the changed lines |
| `truapply run` | One full pass: find, score, tailor, apply, write the summary. `--dry-run`, `--site`, `--limit`, `--show` |
| `truapply tracker` | Opens the local tracker page |
| `truapply finish` | Opens every job waiting for you in one browser, a tab each, filled in and stopped before Submit; you do any human check and press Submit |
| `truapply add LINK` | Adds a company from a Greenhouse, Lever or Ashby job or careers link and checks it now and on every run |
| `truapply schedule` / `unschedule` | Runs it every 3 hours in the background (macOS launchd, Windows Task Scheduler; prints a cron line on Linux) |
| `truapply boards --new` | Prints the career boards you found that aren't in the shared list yet, ready to contribute |
| `truapply archive` | Finds new companies in the latest web archive (no AI); the tracker and weekly runs start it in the background |

Job sources: **career pages** (Greenhouse, Lever, Ashby) and **LinkedIn Easy Apply, Naukri, Indeed, Wellfound**.

### v1 doesn't

| Left out | Why | What happens instead |
|---|---|---|
| Workday, iCIMS, Taleo and other sites that need an account per company | Every company needs a separate account and password | Marked `external` with the link: apply yourself |
| Solving CAPTCHAs or email/SMS codes | Getting past them is deceptive and breaks site rules | The job is flagged `needs_input` |
| Reading your email | Dropped on 28 Oct 2026: an inbox password can read all your mail, and the risk isn't worth it | You mark what happened yourself |
| Windows scheduling | Different system; later | `truapply run` still works by hand |
| A hosted or cloud version | It's meant to stay on your machine | — |

---

## Build phases

A phase is **done only when every must-pass box is ticked**. Nothing is submitted to a real employer until the owner says yes.

```mermaid
flowchart LR
  P0[0 Plan] --> P1[1 Foundation] --> P2[2 Career pages] --> P3[3 Tracker] --> P4[4 Background] --> P4b[4b More companies]
  P4b --> P5[5 Logged-in sites] --> P7[7 Release]
```

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
- The general form filler, plus a local multi-step test form

**Must pass**
- [x] 20 boards polled: 100 % of jobs have a title, company, location, link and description
- [x] Local test form (every field type, 3 steps): 10/10 submitted and detected as success
- [x] Dry run on 10 real Greenhouse/Lever/Ashby forms: ≥ 9 reach Submit with every required field filled (screenshots reviewed)
- [x] A job post with hidden instructions ("ignore your rules…") changes nothing: no tools used, answers still from the profile
- [x] A job post saying "no AI-generated applications" is skipped. A form box "I did not use AI" is never ticked.
- [x] The same job from two sources is applied to once
- [x] A removed job (API 404), or an Ashby job past its deadline to apply, is marked `closed`, not `failed`

### Phase 3 · Tracker page and learning from you

**Builds**
- Application list with filters
- "Needs your answer" and approvals. You can edit any answer before approving.
- Resume change view, and a "what was sent" view per application
- 👍 / 👎 buttons, dismiss reasons, and resume tailoring notes
- A "Tell TruApply" box for plain-language rules
- The "What it learned" page
- Trust counter and the auto-submit offer
- A "Ready for you to apply" list (it replaced "Finish these"): **Open in my Chrome** opens the job, the TruApply extension fills it with the tailored resume and saved answers, and you do any picture check ("prove you're human") and press Submit. TruApply never solves the check itself.
- A count of how often each site shows a check, so jobs on sites without checks are tried first

**Must pass**
- [x] Every status is visible and filterable
- [x] A picture check that appears after Submit puts the job in "Finish these" with every answer saved, never in `unconfirmed` or `failed`
- [x] From "Ready for you to apply", the job opens filled in your own Chrome; submitting it, or **I submitted it**, sets `applied` (14 real applications sent this way, plus a browser test)
- [x] Answer a question on the page, and the next form with that question fills without an AI call (shown in the log)
- [x] Edit an answer before approving → the next form with that question uses your version
- [x] Approve → submitted on the next run (with `--send`, or the Run page's send box); dismiss → never applied
- [x] Dismiss 3 jobs as "too senior" → a suggestion to add that title word to "skip titles" appears, and nothing changes until you accept it
- [x] A rule typed in "Tell TruApply" ("no staffing agencies") changes the next scores, appears on "What it learned", and can be deleted there
- [x] A tailoring note ("don't change my headline") is followed in the next 5 tailored resumes
- [x] The auto-submit suggestion appears exactly after 20 clean approvals in a row; an edit or a 👎 resets the count; **Turn on now** switches it on sooner
- [x] Two 👎 in the last 10 auto-submitted → auto-submit turns off and a notification is sent
- [x] The change view shows exactly the changed lines for 5 tailored resumes
- [x] A POST from another website is rejected (curl test with a fake `Origin`)
- [x] Checked in a real browser, with a screenshot

### Phase 3b · React tracker and the workflow map

**Builds**
- The tracker as a React + TypeScript app (`web/`, built with Vite and shipped prebuilt inside the package, so users don't need Node), talking to the Python tracker only through the JSON API in [tracker-api.md](tracker-api.md)
- Inline answer editing, live run progress without reloads
- **Workflow map** (`/workflow`, removed on 2026-10-29: Today's pipeline counts replace it): a live decision-flow chart of how every job is handled, in the style of a Notion decision diagram. Questions are nodes with YES / NO branches, outcomes are boxes with live job counts, and automatic steps (AI scoring, tailoring, form filling) are dashed purple lines. Clicking a box opens those jobs. The flow:
  - Found on a career page → Title fits your keywords? → Location fits where you'll work? → Seen before? (duplicate) → AI score at least your minimum, with no deal-breaker? (no → Not a fit) → Employer bans AI-written applications? (yes → Skipped)
  - → Tailor the resume → Passes the fact check? (no → original resume used) → Fill the form → Legal question it can't answer? (yes → Needs your answer) → Picture check? (yes → Finish these)
  - → Auto-submit earned and score ≥ 80? (yes → Sent automatically) / (no → Waiting for your OK → Approve? yes → Sent on the next run, no → Dismissed) → Confirmation shown? (yes → Applied, no → Unconfirmed)
- The Revert-to-original-resume button (suggests a tailoring note), and the tracker choosing a free port when 8765 is taken

**Must pass**
- [x] Every page of the current tracker works in the React app, with the same safety checks (Host, Origin, JSON-only POST, strict CSP with only the tracker's own scripts)
- [x] The workflow map's counts match the Career jobs page for every box, and each box links to exactly those jobs
- [x] Checked in a real browser, light and dark, with screenshots of every page; a browser test also checks phone width has no sideways scrolling (a phone layout isn't needed for now)

### Phase 4 · Background runs and daily summary

**Builds**
- `schedule` / `unschedule`
- A run lock, daily limits and pauses
- Crash recovery and a daily Claude call budget
- Daily summary and notifications
- `doctor`

**Must pass**
- [ ] After `schedule`, a run starts on its own and writes the log
- [x] A second run started during a first exits with "already running"
- [x] A run killed right after clicking Submit → the next run marks the job `unconfirmed` and does **not** submit again
- [x] The daily limit and the LinkedIn limit stop applying at exactly the limit
- [x] The summary notification shows once a day
- [x] `doctor` names each broken piece and its fix (tested by breaking each one)

### Phase 4b · More companies

Most Indian startups don't use Greenhouse, Lever or Ashby. A check of 975 Bengaluru startups' careers pages found Keka on 41, Google Forms on 30, Darwinbox on 27, Greenhouse, Lever and Ashby together on 28, Wellfound on 17, Zoho Recruit on 15 and Workday on 14; the rest load their links with JavaScript or post only on job sites. The measure is **relevant open jobs found per week**. In order, each its own change:

1. **Companies from the web archive.** The free Common Crawl index lists every Greenhouse, Lever and Ashby page it has visited. A partial read on 28 Oct 2026 gave 2,353 names we didn't have, 210 of them with jobs in India. Read in the background beside runs, once a week or from **Search the web archive**; only new names are checked, and no AI is used.
1. **Companies by name.** Paste company names or websites on the Companies page; each is tried on Greenhouse, Lever and Ashby, and kept only when it has jobs in your country, so a same-named company abroad isn't added.
2. **Companies from every job.** Any job whose apply link or description points to a Greenhouse, Lever or Ashby board adds that company.
3. **Many small web searches.** One search per role, place and job system instead of one per job system, within the daily Claude budget.
4. **Keka and Darwinbox.** Only if their job lists can be read without signing in. Then Zoho Recruit.

SmartRecruiters and Workday stay out (dropped on 28 Oct 2026).

**Must pass**
- [x] The built-in list has the 17 Bengaluru companies found on Greenhouse, Lever and Ashby
- [x] The web archive adds companies with jobs in your country, reads each crawl once, retries pages that time out, and checks a name again only after 180 days
- [x] Pasting a name that matches a board with jobs in your country adds it; one with jobs only abroad is not added
- [ ] A Wellfound or pasted job linking to a Greenhouse, Lever or Ashby board adds that company
- [ ] The weekly web search finds more new companies than before, and stays within the daily Claude budget
- [ ] Keka and Darwinbox: a read-only test shows whether jobs can be listed without signing in

### Phase 5 · Logged-in sites

One at a time: **LinkedIn → Naukri → Indeed → Wellfound.** Must pass, for each site:
- [ ] `doctor` detects logged in and logged out
- [ ] Search finds ≥ 10 relevant jobs, read-only, with no errors
- [ ] Saved page fixtures (search page and job page, personal data removed) are in `tests/fixtures/<site>/`, and the tests pass on them
- [ ] 5 dry runs reach Submit
- [ ] A block or "unusual activity" page pauses the site for the day (fixture test)
- [ ] "Apply on company site" links to Greenhouse/Lever/Ashby are followed; other links are marked `external`
- [ ] With the owner's OK: 3 live applications, each confirmed by the site

### Phase 6 · Replies and learning from results

**Dropped on 28 Oct 2026.** Reading your inbox needs a password that can read all your mail, so TruApply never connects to email.

### Phase 7 · Open-source release

**Builds**
- README (install, disclaimer), MIT LICENSE, CONTRIBUTING
- Issue and PR templates, CHANGELOG
- Shared company list of ≥ 300 companies
- Version `0.1.0`

**Must pass**
- [ ] Fresh macOS user account: README install → first dry run in ≤ 15 min
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
