# Examples

Real shapes of the data TruApply works with. Every person, company and number here is made up.

## Profile — `~/.truapply/profile.json`

```json
{
  "name": "Asha Rao",
  "email": "asha.rao@example.com",
  "phone": "+91 90000 00000",
  "city": "Bengaluru",
  "country": "India",
  "links": ["https://github.com/asharao", "https://linkedin.com/in/asharao"],
  "current_company": "Acme Analytics",
  "years_experience": 2.5,
  "resume": { "format": "latex", "path": "~/.truapply/resume/master.tex" },
  "roles": ["Frontend Engineer", "React Developer", "UI Engineer"],
  "title_keywords": ["frontend", "front-end", "react", "ui engineer", "javascript"],
  "title_exclude": ["senior", "staff", "principal", "lead", "manager", "intern"],
  "work_places": {
    "onsite_city": true,
    "remote_country": true,
    "relocate": true,
    "relocate_cities": ["Hyderabad", "Pune"],
    "remote_abroad": true
  },
  "unknown_questions": "skip",
  "daily_cap": 20,
  "cover_letter": "required",
  "skip_companies": ["Acme Analytics"],
  "notice_period": "30 days",
  "citizenship": "India",
  "work_without_visa": ["India"],
  "needs_sponsorship_elsewhere": true,
  "salary": { "currency": "INR", "expected_min": 1200000, "expected_max": 1800000, "current": 800000 },
  "dob": null,
  "diversity": null,
  "extra_facts": "Speaks English, Hindi and Kannada.",
  "settings": {
    "min_score": 60, "linkedin_cap": 10, "run_every_minutes": 180, "summary_hour": 20,
    "ai_calls_per_day": 300, "max_job_age_days": 30, "company_search": "weekly",
    "tailor_resume": true, "auto_submit": false, "auto_submit_score": 80,
    "wellfound": true, "wellfound_roles": [], "wellfound_titles": [], "wellfound_skip": [],
    "jobs_per_run": 5, "scores_per_run": 40
  },
  "version": 1
}
```

## Shared company list — `truapply/sources/companies.csv`

```csv
ats,slug,company,tags
ashby,fabrikam,Fabrikam,remote
greenhouse,northwind,Northwind,india;remote
lever,contoso,Contoso,india
```

## Scoring a job

**Prompt** (shortened):

```
Score how well this job fits the candidate, from 0 to 100.

<candidate>
Target roles: Frontend Engineer, React Developer, UI Engineer
Experience: 2.5 years
Based in: Bengaluru, India
Will work: on-site or hybrid in Bengaluru; remote within India; relocating within India to Hyderabad, Pune; remote for companies abroad (without moving)
Can work without a visa in: India
Needs visa sponsorship elsewhere: yes
Yearly salary wanted: 1,200,000-1,800,000 INR
Notice period: 30 days
</candidate>

<resume>
…
</resume>

The candidate's own preferences. Use them to judge fit. …
<preferences>
- No staffing-agency jobs
- Pune is fine, Mumbai is not
</preferences>

<job>
Frontend Engineer II at Northwind (Remote, India)

We're looking for 2–4 years of React and TypeScript … dashboards … design system …
</job>

- `dealbreaker`: …
- `forbids_ai`: …
- `score`: …
- `reason`: …
```

The preferences are the rules you typed in **Tell TruApply**. Text inside `<job>` is data from a website, never instructions.

**Reply** (checked against the schema):

```json
{
  "score": 86,
  "reason": "+ React and TypeScript dashboards match; + design-system work matches; + remote in India works",
  "dealbreaker": null,
  "forbids_ai": false
}
```

A score under `min_score`, a deal-breaker, or `forbids_ai: true` marks the job `skipped` with the reason.

## Filling a form

The Chrome extension reads the form in your tab and sends its fields to the app (`POST /api/extension/jobs/41/answers`):

```json
[
  { "id": "f1",  "kind": "text",     "label": "First Name", "required": true, "options": [], "value": "", "max_length": null },
  { "id": "f4",  "kind": "file",     "label": "Resume/CV", "required": true, "options": [], "value": "", "max_length": null },
  { "id": "f7",  "kind": "select",   "label": "Are you legally authorized to work in India?", "required": true, "options": ["Yes", "No"], "value": "", "max_length": null },
  { "id": "f8",  "kind": "radio",    "label": "Will you now or in the future require visa sponsorship?", "required": true, "options": ["Yes", "No"], "value": "", "max_length": null },
  { "id": "f9",  "kind": "text",     "label": "How many years of experience do you have with React?", "required": true, "options": [], "value": "", "max_length": null },
  { "id": "f10", "kind": "textarea", "label": "Why do you want to work at Northwind?", "required": false, "options": [], "value": "", "max_length": 2000 },
  { "id": "f11", "kind": "checkbox", "label": "I confirm I did not use AI tools to prepare this application", "required": true, "options": [], "value": "", "max_length": null }
]
```

- `f1` comes from the profile and `f7` from a saved answer, so no AI call is needed for them.
- `f4` gets the tailored resume.
- `f11` is a confirmation box, so it's left for you. It never goes to the AI and is never ticked.
- Only `f8`–`f10` go to the AI.

**AI reply** (checked against the schema):

```json
{
  "answers": [
    { "id": "f8",  "value": "No", "reusable": false, "guessed": false },
    { "id": "f9",  "value": "2", "reusable": true, "guessed": false },
    { "id": "f10", "value": "Your design-system work matches what I built at Acme Analytics: 40 shared components used across three products…", "reusable": false, "guessed": false }
  ],
  "unknown": [],
  "blocker": null,
  "skip_reason": null,
  "cover_letter": null
}
```

- `f8` isn't reusable, because the answer depends on the job's country (a US job would get "Yes").
- `f9` is saved and reused on every future form. It was worked out from the resume dates.
- A legal question the profile doesn't answer would come back in `unknown` with `legal: true`, and be left for you.

**What the app sends back to the extension:**

```json
{
  "answers": [
    { "id": "f1", "value": "Asha" },
    { "id": "f4", "value": "RESUME" },
    { "id": "f7", "value": "Yes" },
    { "id": "f8", "value": "No" },
    { "id": "f9", "value": "2" },
    { "id": "f10", "value": "Your design-system work matches what I built at Acme Analytics: …" }
  ],
  "forYou": [
    { "id": "f11", "label": "I confirm I did not use AI tools to prepare this application", "why": "only you can agree to or confirm this", "consent": true }
  ],
  "waiting": [],
  "note": null
}
```

The extension fills the fields, attaches the resume, and outlines `f11` for you. You check the form and press Submit.

## Resume change view

```
Northwind · Frontend Engineer II                         checks: numbers ✔  no new claims ✔  1 page ✔

  SUMMARY
- Frontend engineer with 2+ years building React and TypeScript apps, plus Node.js APIs.
+ Frontend engineer with 2+ years building React and TypeScript dashboards and design systems, plus Node.js APIs.

  SKILLS
- Frontend: React, Next.js, Redux Toolkit, Tailwind CSS, Storybook
+ Frontend: React, Storybook, Redux Toolkit, Next.js, Tailwind CSS

  EXPERIENCE · Acme Analytics
  (bullet 3 moved to the top)
```

"Dashboards" and "design systems" were already in her experience bullets, so the check passes.

## Tracker page — Today

```
┌ TruApply ─────────┬──────────────────────────────────────────────────────────┐
│ Today             │ Tuesday, 27 October                        All jobs →    │
│ Jobs              │ 3 jobs are ready for you                                 │
│ All jobs          │ ✦ 1 suggestion from jobs you dismissed. Review them →    │
│ Companies         ├ Apply next ──────────────────────────────────────────────┤
│ Activity          │ The TruApply extension fills it in; you check it and     │
│                   │ press Submit.            [Send these with auto-submit]   │
│ Learned           │ N  Frontend Engineer II                                  │
│ Settings          │    Northwind · Remote, India · Careers page   86  2h ago │
│                   │ C  UI Engineer                                           │
│ [▶ Run now]       │    Contoso · Bengaluru · Careers page         81  3h ago │
│                   ├ Pipeline ────────────────────────────────────────────────┤
│                   │ Found 1,284 · Not a fit 212 · Good matches 9 ·           │
│                   │ Ready for you 3 · Applied 14                             │
│                   ├ Recently applied ─────────────────────────── See all 14 →┤
│                   │ F  React Developer                                       │
│                   │    Fabrikam · Remote, India · LinkedIn        78  1d ago │
└───────────────────┴──────────────────────────────────────────────────────────┘
```

Job statuses: `new`, `skipped`, `scored`, `ready`, `dismissed`, `applied`, `closed`. Open a job to see the match reasons, the resume changes, **Open in my Chrome**, **I submitted it**, 👍 / 👎 and **Dismiss**.

## "What it learned" page

```
Suggestions (1)
  Skip jobs with "staff" in the title?                   [Skip them] [No thanks]
Your rules (2)
  ✎ ✕  No staffing-agency jobs
  ✎ ✕  Pune is fine, Mumbai is not
Tailoring notes (1)
  ✎ ✕  Don't change my headline
Saved answers (38)
  ✎    How many years of experience do you have with React?   2   AI
```

A suggestion shows up after you dismiss 3 jobs as "too senior" that share a title word. Nothing changes until you accept it.

## Daily summary — `~/.truapply/summaries/2026-10-27.md`

```
# TruApply · 27 Oct 2026

- Applied today: 4
- Prepared today: 5
- Ready for you to apply: 3
- Claude calls today: 61 of 300

Open them from your tracker; the extension fills them in your Chrome.
```

It's written once a day after `summary_hour`, with a notification: "TruApply today: 4 applied · 3 ready for you to apply".

## Run log — `~/.truapply/runs/20261027-150002-123456.log`

One file per run. The tracker's Activity page reads it.

```
Automatic run
Checking company career pages …
  1,284 open jobs · 38 new ones fit your titles and places
Checking Wellfound …
  2 new Wellfound jobs fit you · listed for you to apply
Scoring 31 jobs with AI …
  1/31 Northwind · Frontend Engineer II: 86, good match
  2/31 Litware · Staff Frontend Engineer: skipped, deal-breaker: asks for 8+ years, has 2.5
  3/31 Tailspin · Frontend Developer: skipped, score 48: - mostly Angular; - asks 5+ years
  …
Tailoring your resume for 2 jobs …
  Northwind · Frontend Engineer II: tailored
  Contoso · UI Engineer: kept your original resume

Summary
Boards: 705 checked · 4 new · 2 gone · 1 unreachable
Jobs: 1,284 open · 212 fit your titles and places · 38 new
Scored: 9 good matches · 22 skipped · 0 to retry
Ready for you to apply in your Chrome:
  ✔ Northwind · Frontend Engineer II
  ✔ Contoso · UI Engineer (your original resume)
```

A run started with `truapply run` or **Run now** starts with `Manual run`. Nothing is ever sent by a run.

## `truapply doctor`

```
✔ Data folder: /Users/asha/.truapply
✔ Database: 1,284 jobs saved
✔ Profile: /Users/asha/.truapply/profile.json
✔ Resume: latex resume builds (1 page)
✔ Claude budget: 37 of 300 calls used today
✔ Claude Code: installed and logged in
✔ Browser: chrome 141.0.7390.54
✔ Tracker page: built
✘ Schedule: The schedule runs /Users/asha/old-venv/bin/python, which no longer exists.
   → Run `truapply schedule` again, or `truapply unschedule` to stop it.
```

Each check that fails names what's broken and the fix. The exit code is 1 when anything is broken. There's no login or email check: TruApply never logs in to job sites and never reads your email.
