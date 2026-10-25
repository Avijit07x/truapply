# Setup questions

`satyaapply setup` asks every new user these questions in the terminal. Each one is either:

- multiple choice: type the number, or press Enter for the recommended option, or
- a short typed answer.

Anything the resume already answers is filled in first, and you just confirm it. The answers are validated and saved to `~/.satyaapply/profile.json`. You can run `satyaapply setup` again, or edit that file, at any time.

```mermaid
flowchart LR
  c[Claude check] --> r[1 Resume] --> j[2 Jobs] --> s[3 Sites] --> a[4 How much it does alone]
  a --> f[5 Form facts] --> d[6 Diversity] --> e[7 Anything else] --> m[8 Email] --> done[Next steps]
```

## Before the questions

**Claude Code check.** Confirms `claude` is installed and logged in by making one tiny call. If it isn't, setup explains how to fix that and stops.

## 1. Resume

**"Where is your resume?"** Accepts `.tex`, `.pdf`, `.docx`, `.md` or `.txt`.

- **LaTeX (`.tex`):** your file is tailored as-is, so your layout stays exactly the same. This needs `pdflatex`. If it's missing, setup offers:
  1. **Install TinyTeX now** (about 100 MB, no admin password; the official installer, run with `--no-path`). Recommended.
  2. I'll install LaTeX myself, then run setup again
  3. Use the clean built-in resume design instead
- **Anything else:** your resume is turned into a clean, one-column HTML resume that hiring software can read. You're asked to open it and check it once.

Setup then builds `master.pdf`. If a LaTeX package is missing, it installs it with `tlmgr`.

**Filled in from the resume, for you to confirm:** name, email, phone, city, country, links, current company, years of experience, skills.

## 2. What jobs to look for

| Question | Type | Notes |
|---|---|---|
| Target job titles | typed, pre-filled | e.g. "Frontend Engineer, React Developer, UI Engineer" |
| Title must contain one of | typed, pre-filled | e.g. "frontend, front-end, react, ui engineer" |
| Skip titles containing | typed, pre-filled for your experience | e.g. "senior, staff, principal, manager, intern" |
| Where are you willing to work? | multiple choice, pick several | On-site/hybrid in *your city* · Remote within *your country* · Other cities in *your country* (you'd relocate) · Remote for companies abroad |
| Which cities? | typed | Only if you'd relocate. Enter = any. |

## 3. Which sites

**"Which job sites should it use?"** Pick several.

| Option | What to know |
|---|---|
| Company career pages (Greenhouse, Lever, Ashby) | No login, no account risk, the most reliable. **Recommended.** |
| LinkedIn | Biggest source. LinkedIn bans accounts it catches using bots. Limited to 10 a day. |
| Naukri | Big in India. Sends the resume on your Naukri profile, not the tailored one. |
| Indeed | Uses your country's Indeed site |
| Wellfound | Startups. Uses your Wellfound profile. |

## 4. How much it does on its own

| Question | Options (recommended first) |
|---|---|
| Submitting | **Review queue first; offer auto-submit once it has earned trust** (after 20 approvals in a row with no edits) · Review queue only, never auto-submit |
| A form question your profile doesn't answer | **Skip the job and flag the question** (your answer is reused from then on) · Best guess from your profile |
| Applications per day, at most | **About 20** · About 50 · No limit (LinkedIn stays at 10 or less either way) |
| Cover letters | **Only when the form requires one** · Every application · Never (skips jobs that require one) |
| Companies to skip | typed; your current employer is added automatically |

> Legal and eligibility questions are **never** guessed, whatever you pick here. See [safety.md](safety.md).

## 5. Facts forms ask for

| Question | Type | Why it's asked |
|---|---|---|
| Notice period | Immediate · 15 days · 30 days · 60 days · 90 days · other | Almost every Indian form, and many others |
| Citizenship | typed, pre-filled from the resume's country | Work-authorization questions |
| Countries you can work in without a visa | typed, pre-filled with your citizenship | "Are you authorized to work in …?" |
| Would you need visa sponsorship elsewhere? | yes / no | "Will you now or in future require sponsorship?" Jobs that need it are skipped. |
| Salary currency | typed, pre-filled from the country (e.g. INR) | |
| Expected salary: lowest and highest | numbers, per year | Jobs clearly paying under the lowest are skipped |
| Current salary | number, optional | Required on Naukri and many Indian forms. Blank means those jobs are skipped. |
| Date of birth | optional | Some Indian forms. Blank means those jobs are skipped. |

## 6. Diversity questions (optional)

**"How should it answer optional diversity questions?"** · **Prefer not to say** (recommended) · Answer them

If you choose to answer them:

| Question | Options | Explanation shown |
|---|---|---|
| Gender | Male · Female · Non-binary · Prefer not to say | |
| Disability | No · Yes · Prefer not to say | |
| Veteran | No · Yes · Prefer not to say | "Have you served in a country's armed forces? Mostly asked by US companies." |
| Race / ethnicity | typed, or Enter for "Prefer not to say" | "Asked by US companies" |

## 7. Anything else

**"Is there anything true about you that isn't on your resume?"** Typed, optional: skills, older projects, certifications, languages spoken. Tailoring and form answers may use this as well as the resume, and **nothing else**.

## 8. Reply tracking (optional, recommended)

**"Track replies from your email?"** · **Yes** · Not now

If yes, setup runs the `satyaapply email` steps from [outcomes.md](outcomes.md#setup): address, app password, test connection.

---

## Settings not asked (defaults)

These are in `profile.json` under `settings`. Change them there, or on the tracker page.

| Setting | Default | Meaning |
|---|---|---|
| `min_score` | 60 | Jobs scoring below this are skipped |
| `strong_score` | 80 | Only jobs scoring this or more are auto-submitted |
| `trust_after` | 20 | Approvals in a row with no edits before auto-submit is offered |
| `linkedin_cap` | 10 | LinkedIn applications per day, at most |
| `run_every_hours` | 3 | How often the background run starts |
| `summary_hour` | 20 | When the daily summary is sent (24 h clock) |
| `ai_calls_per_day` | 300 | Daily Claude call budget |
| `ghosted_after_days` | 21 | No reply after this many days = ghosted |
| `max_job_age_days` | 30 | Older postings are ignored |

## After setup

```
satyaapply login            # log in to the job sites once
satyaapply doctor           # check everything works
satyaapply run --dry-run    # try it: fills forms, submits nothing
satyaapply tracker          # see what it did
satyaapply schedule         # run it every 3 hours in the background
```
