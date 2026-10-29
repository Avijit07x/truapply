# Setup questions

Every new user answers these once. There are two ways:

- **In the tracker app (the main way).** Run `truapply tracker --open`. Until setup is done, the app opens on **Set up** and every other page is locked.
- **In the terminal.** `truapply setup` asks the same core questions, plus a few more, one at a time.

Either way, the answers are checked and saved to `~/.truapply/profile.json`. Change anything later on the tracker's Settings page, or edit that file.

## In the tracker app: 5 steps

```mermaid
flowchart LR
  r[1 Your resume] --> d[2 Your details] --> p[3 Rights and pay] --> h[4 How it runs] --> x[5 Extension] --> t[Today]
```

### 1. Your resume

**"Choose your resume."** PDF, Word, LaTeX, Markdown or plain text, up to 5 MB. Claude reads it once, which takes about a minute.

- **LaTeX (`.tex`) with `pdflatex` installed:** your file is tailored as-is, so your layout stays the same.
- **Anything else, or LaTeX without `pdflatex`:** the content moves into the clean, one-column built-in design that hiring software can read.

### 2. Your details

| Question | Notes |
|---|---|
| Full name, email, phone, city, country | Filled in from your resume. Phone is optional. |
| Job titles you want | Suggested from your resume |
| A job title must contain one of | Suggested from your resume. At least one is needed. |
| Where you'll work | Pick at least one: on-site or hybrid in *your city* (on by default) · remote within *your country* (on by default) · other cities (you'd move) · remote for companies abroad |

### 3. Rights and pay

These are never filled in for you, because TruApply never guesses them.

| Question | Notes |
|---|---|
| Citizenship | |
| Countries you can work in without a visa | At least one |
| Would you need visa sponsorship to work in other countries? | Yes / No |
| Notice period | Immediate · 15 days · 30 days · 60 days · 90 days |
| Currency | Suggested from your country (e.g. INR) |
| Lowest salary you'd accept, highest you'd ask for | Yearly amounts |

### 4. How it runs

| Question | Options |
|---|---|
| When should it run? | Only when I press Run · Every hour · Every 3 hours · Once a day. Shown only where automatic runs work (macOS and Windows). |
| Your resume for each job | Tailor it to each job · Send it as it is |
| Jobs to get ready each run | 1 to 50 (starts at 5) |

### 5. Chrome extension

Install steps for the TruApply extension, with a live check that turns green once it's installed. The extension fills applications in your own Chrome; you check each one and press Submit. **Finish without it** skips this step; add it later from Settings.

After **Finish setup**, the built-in company list is added, automatic runs start if you picked a time, and the app opens on **Today**.

### Not asked in the app

These take a default. Change them on the Settings page.

| What | Default |
|---|---|
| Skip titles containing | Suggested by Claude from your resume |
| Links, current company, years of experience | Taken from your resume |
| A form question your profile doesn't answer | Skip the job and flag the question |
| Applications per day, at most | 20 |
| Cover letters | Only when the form requires one |
| Companies to skip | Your current employer |
| Current salary, date of birth | Blank |
| Diversity questions | Prefer not to say |
| Anything else true about you | Blank |

## In the terminal: `truapply setup`

Each question is either multiple choice (type the number, or press Enter for the recommended option) or a short typed answer. Anything the resume answers is filled in first, and you just confirm it. If a profile already exists, it asks before replacing it.

```mermaid
flowchart LR
  c[Claude check] --> r[Resume] --> b[1 About you] --> j[2 Jobs] --> a[3 How much it does alone]
  a --> f[4 Form facts] --> d[5 Diversity] --> e[6 Anything else] --> done[Next steps]
```

### Before the questions

**Claude Code check.** Confirms `claude` is installed and logged in by making one tiny call. If it isn't, setup explains how to fix that and stops.

**"Where is your resume?"** Accepts `.tex`, `.pdf`, `.docx`, `.md` or `.txt` (or pass `--resume PATH`).

- **LaTeX (`.tex`):** your file is tailored as-is. This needs `pdflatex`. If it's missing, setup offers:
  1. **Install TinyTeX now** (about 100 MB, no admin password, official installer). Recommended.
  2. I'll install LaTeX myself, then run setup again
  3. Use the built-in resume design instead
- **Anything else:** your resume moves into the clean, one-column built-in design. You're asked to open it and check it once.

### 1. About you

Filled in from your resume, for you to confirm: full name, email, phone, city, country, links, current company, years of experience.

### 2. What jobs to look for

| Question | Type | Notes |
|---|---|---|
| Target job titles | typed, pre-filled | e.g. "Frontend Engineer, React Developer, UI Engineer" |
| A job title must contain one of | typed, pre-filled | e.g. "frontend, front-end, react, ui engineer" |
| Skip titles containing | typed, pre-filled | e.g. "senior, staff, principal, manager, intern" |
| Where are you willing to work? | pick several | On-site or hybrid in *your city* · Remote within *your country* · Other cities in *your country* (you'd relocate) · Remote for companies abroad |
| Which cities? | typed | Only if you'd relocate. Enter = any city. |

### 3. How much it does on its own

It says first: legal and eligibility questions are never guessed, and it never submits for you.

| Question | Options (recommended first) |
|---|---|
| A form question your profile doesn't answer | **Skip the job and flag the question** (your answer is saved and reused) · Best guess from your profile |
| Applications per day, at most | **About 20** · About 50 · No limit (LinkedIn stays at 10 or less) |
| Cover letters | **Only when the form requires one** · Every application · Never (skips jobs that require one) |
| Companies to skip | typed; your current employer is added automatically |

> Legal and eligibility questions are **never** guessed, whatever you pick here. See [safety.md](safety.md).

### 4. Facts forms ask for

| Question | Type | Why it's asked |
|---|---|---|
| Notice period | Immediate · 15 days · 30 days · 60 days · 90 days · Other | Almost every Indian form, and many others |
| Citizenship | typed, pre-filled with your country | Work-authorization questions |
| Countries you can work in without a visa | typed, pre-filled with your citizenship | "Are you authorized to work in …?" |
| Would you need visa sponsorship to work in other countries? | yes / no | "Will you now or in future require sponsorship?" |
| Salary currency | typed, pre-filled from the country (e.g. INR) | |
| Lowest and highest yearly salary | numbers, like 1200000 or 12 LPA | |
| Current yearly salary | number, optional | Some forms require it |
| Date of birth | optional | Some forms require it |

### 5. Diversity questions (optional)

**"How should it answer optional diversity questions?"** · **Prefer not to say** (recommended) · Answer them

If you choose to answer them:

| Question | Options | Explanation shown |
|---|---|---|
| Gender | Male · Female · Non-binary · Prefer not to say | |
| Disability | No · Yes · Prefer not to say | |
| Veteran | No · Yes · Prefer not to say | "Have you served in a country's armed forces? Mostly asked by US companies." |
| Race / ethnicity | typed, or Enter for "Prefer not to say" | "Asked by US companies" |

### 6. Anything else

**"Anything true about you that isn't on your resume?"** Typed, optional: skills, older projects, certifications, languages spoken. Tailoring and form answers may use this as well as the resume, and **nothing else**.

Setup then builds `master.pdf` (missing LaTeX packages install automatically) and prints the next steps.

The terminal setup doesn't ask how often to run, whether to tailor, or about the extension. Those keep their defaults; set them in the tracker's Settings, or run `truapply schedule`.

## Settings not asked (defaults)

These are in `profile.json` under `settings`. Every one of them, and every answer above, can be changed on the tracker's Settings page.

| Setting | Default | Meaning |
|---|---|---|
| `min_score` | 60 | Jobs scoring below this are skipped |
| `jobs_per_run` | 5 | Jobs got ready each run (asked in the app) |
| `scores_per_run` | 40 | Jobs scored each run |
| `tailor_resume` | true | Tailor the resume to each job (asked in the app) |
| `run_every_minutes` | 180 | Minutes between automatic runs, once they're on (15 to 1,440) |
| `auto_submit` | false | Let the extension press Submit on its own. Off until you turn it on. |
| `auto_submit_score` | 80 | Auto-submit sends only jobs scoring this or more |
| `linkedin_cap` | 10 | LinkedIn jobs got ready per day, at most |
| `company_search` | weekly | How often to search the web for new companies (off, daily, weekly) |
| `wellfound` | true | Check Wellfound for jobs on each run |
| `summary_hour` | 20 | When the daily summary is written (24 h clock) |
| `ai_calls_per_day` | 300 | Daily Claude call budget |
| `max_job_age_days` | 30 | Older postings are ignored |

## After setup

**From the app:** you land on **Today**. Press **Run now** to find your first jobs.

**From the terminal**, setup prints:

```
truapply doctor                       check that everything works
truapply tailor JOB.txt --company … --title …   preview a tailored resume
```

Then `truapply tracker --open` to see the tracker, and `truapply run` for a run.
