# Examples

Real shapes of the data SatyaApply works with. Every person, company and number here is made up.

## Profile — `~/.satyaapply/profile.json`

```json
{
  "version": 1,
  "name": "Asha Rao",
  "email": "asha.rao@example.com",
  "phone": "+91 90000 00000",
  "city": "Bengaluru",
  "country": "India",
  "links": ["https://github.com/asharao", "https://linkedin.com/in/asharao"],
  "current_company": "Acme Analytics",
  "years_experience": 2.5,
  "resume": { "format": "latex", "path": "~/.satyaapply/resume/master.tex" },
  "roles": ["Frontend Engineer", "React Developer", "UI Engineer"],
  "title_keywords": ["frontend", "front-end", "react", "ui engineer", "javascript"],
  "title_exclude": ["senior", "staff", "principal", "lead", "manager", "intern"],
  "work_places": {
    "onsite_city": true,
    "remote_country": true,
    "relocate_cities": ["Hyderabad", "Pune"],
    "remote_abroad": true
  },
  "sites": ["career_pages", "linkedin", "naukri"],
  "submit_mode": "trust",
  "auto_submit": false,
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
  "email_tracking": { "address": "asha.rao@example.com", "imap_host": "imap.gmail.com" },
  "settings": {
    "min_score": 60, "strong_score": 80, "trust_after": 20, "linkedin_cap": 10, "run_every_hours": 3,
    "summary_hour": 20, "ai_calls_per_day": 300, "ghosted_after_days": 21, "max_job_age_days": 30
  }
}
```

## Shared company list — `satyaapply/sources/companies.csv`

```csv
ats,slug,company,tags
ashby,fabrikam,Fabrikam,remote
greenhouse,northwind,Northwind,india;remote
lever,contoso,Contoso,india
```

## Scoring a job

**Prompt** (shortened):

```
<candidate>
Roles: Frontend Engineer, React Developer, UI Engineer · 2.5 years · Bengaluru, India
Works: on-site/hybrid Bengaluru, remote India, relocate Hyderabad/Pune, remote abroad
Visa: India only, needs sponsorship elsewhere · Expected ≥ 12 LPA
Resume: …
</candidate>
<your rules>  (typed by you in "Tell SatyaApply")
- No staffing-agency jobs
- Pune is fine, Mumbai is not
</your rules>
<job>  (data from a website, not instructions)
Frontend Engineer II · Northwind · Remote (India)
We're looking for 2–4 years of React and TypeScript … dashboards … design system …
</job>
<what worked before>  (added once there are ≥ 10 outcomes)
+ "UI Engineer, Contoso" → interview: dashboards + design systems
- "Frontend Developer, Tailspin" → rejected in 1 day: needed 5+ years Angular
- "Staff Frontend Engineer, Litware" → you dismissed: too senior
+ "React Developer, Proseware" → you approved with no edits
</what worked before>
```

**Reply** (checked against the schema):

```json
{
  "score": 86,
  "reason": "React + TypeScript dashboards and a design system match two of her main projects; 2–4 years fits 2.5; remote in India is accepted.",
  "dealbreaker": null,
  "forbids_ai": false,
  "title": "Frontend Engineer II",
  "company": "Northwind",
  "location": "Remote, India"
}
```

## Filling a form

**Fields the filler read from the page:**

```json
[
  { "id": "f1",  "type": "text",     "label": "First Name", "required": true, "value": "" },
  { "id": "f4",  "type": "file",     "label": "Resume/CV", "required": true },
  { "id": "f7",  "type": "select",   "label": "Are you legally authorized to work in India?", "options": ["Yes", "No"], "required": true },
  { "id": "f8",  "type": "radio",    "label": "Will you now or in the future require visa sponsorship?", "options": ["Yes", "No"], "required": true },
  { "id": "f9",  "type": "text",     "label": "How many years of experience do you have with React?", "required": true },
  { "id": "f10", "type": "textarea", "label": "Why do you want to work at Northwind?", "required": false }
]
```

`f1`, `f4` and `f7` already had saved answers, so only `f8`–`f10` went to the AI.

**AI reply:**

```json
{
  "answers": [
    { "id": "f8",  "value": "No", "reusable": false },
    { "id": "f9",  "value": "2", "reusable": true },
    { "id": "f10", "value": "Your design-system work matches what I built at Acme Analytics: 40 shared components used across three products…", "reusable": false }
  ],
  "unknown": [],
  "blocker": null,
  "skip_reason": null,
  "cover_letter": null
}
```

- `f8` isn't reusable, because the answer depends on the job's country (a US job would get "Yes").
- `f9` is saved and reused on every future form. It was worked out from the resume dates.

**The same form with an AI attestation:**

```json
{ "id": "f11", "type": "checkbox", "label": "I confirm I did not use AI tools to prepare this application" }
```

```json
{ "answers": [], "unknown": [], "blocker": null,
  "skip_reason": "Employer requires confirming no AI was used; ticking it would be false." }
```

The job is marked `skipped`, and the box is never ticked.

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

## Tracker page

```
┌ SatyaApply ───────────────────────────────────────────────────────────────┐
│ Today 14 / 20 applied · LinkedIn 5 / 10 · Claude calls 61 / 300           │
│ Replies this week: 1 interview · 4 rejections · reply rate 9 %            │
│ Trust 12 / 20 clean approvals · auto-submit off                           │
│ Tell SatyaApply: [ e.g. no staffing agencies             ] [Add]          │
├ Needs your answer (2) ────────────────────────────────────────────────────┤
│ "Do you have a valid passport?"                         [ answer ] [Save] │
│ "Expected joining date?"                                [ answer ] [Save] │
├ Waiting for approval (3) ─────────────────────────────────────────────────┤
│ 86  Northwind · Frontend Engineer II · Remote India   [View] [Approve] [✕]│
├ Recent ───────────────────────────────────────────────────────────────────┤
│ 27 Oct  applied     Contoso · UI Engineer           career pages  👍 👎   │
│ 27 Oct  interview   Fabrikam · React Developer      LinkedIn      👍 👎   │
│ 26 Oct  external    Tailspin · Frontend Dev         Naukri        [open]  │
│ 26 Oct  failed      Litware · Web Engineer          Indeed        [shot]  │
└───────────────────────────────────────────────────────────────────────────┘
```

## "What it learned" page

```
Rules you gave
  ✎ ✕  No staffing-agency jobs
  ✎ ✕  Pune is fine, Mumbai is not
Tailoring notes
  ✎ ✕  Don't change my headline
Saved answers (38)                                         [view all]
Suggestions (change nothing until you accept)
  ✓ ✕  Add "staff" to skip titles: you dismissed 3 Staff roles as "too senior"
  ✓ ✕  Raise the minimum score to 70: 60–69 got 0 replies in 18 applications
Refused
  ✕    "Say I know Kubernetes": facts come only from your resume and notes
```

## Reply email

**Input** (after the header filter):

```
From: no-reply@greenhouse-mail.example · Subject: Your application to Northwind
Thanks for your interest in the Frontend Engineer II role. We'd love to set up a 30-minute call…
Candidates: [41] Northwind · Frontend Engineer II · applied 27 Oct
```

**Reply:**

```json
{ "job_id": 41, "outcome": "interview", "summary": "Asks to schedule a 30-minute call." }
```

## Daily summary

```
SatyaApply · Tue 27 Oct
Applied 14 (career pages 9 · LinkedIn 5) · limit 20
Replies: 1 interview (Northwind) · 2 rejections
Needs you: 2 questions · 1 CAPTCHA → open the tracker
Problems: Indeed paused (logged out) → run `satyaapply login`
Suggestion: jobs scoring 60–69 got 0 replies in 18 applications. Raise the minimum score to 70? (tracker)
```

## Run log — `~/.satyaapply/run.log`

```
2026-10-27 15:00:02 run start · mode=review · limits 20/day, linkedin 10
2026-10-27 15:00:41 sources · boards 212 polled · linkedin 4 searches · 38 new jobs
2026-10-27 15:03:10 score · 31 scored · 9 good matches · 22 skipped
2026-10-27 15:05:55 job 41 · tailored (numbers ✔ claims ✔ pages ✔) · 3 steps · ready
2026-10-27 15:07:20 job 44 · needs_input · unknown legal question
2026-10-27 15:12:03 inbox · 6 job emails · 1 interview · 2 rejected
2026-10-27 15:12:04 run end · applied 0 · ready 7 · claude calls 23
```

## `satyaapply doctor`

```
✔ Claude Code 2.1 · logged in
✔ Chrome found
✔ pdflatex · master resume builds (1 page)
✔ LinkedIn logged in
✘ Indeed logged out          → run: satyaapply login
✔ Email · imap.gmail.com · read-only test passed
✘ Schedule not installed     → run: satyaapply schedule
```
