# Tracker API

The tracker page is a React app (`web/`) served by the Python tracker (`satyaapply tracker`). The app talks to the tracker only through this JSON API. Everything runs on `127.0.0.1`; nothing leaves your computer.

The TypeScript shapes below are the same ones the app uses, in `web/src/api/types.ts`. Tests in `tests/unit/test_tracker*.py` check every endpoint.

## Rules for every request

- Only `Host: 127.0.0.1:<port>` or `localhost:<port>` is answered (this blocks DNS-rebinding tricks). Anything else gets `403`.
- Every `POST` needs `Origin: http://127.0.0.1:<port>` (or `localhost`) **and** `Content-Type: application/json`. Anything else gets `403`.
- Bodies are JSON objects, at most 200 KB. A bigger body gets `403`; a body that isn't a JSON object gets `400`.
- Errors are `{ error: string, problems?: string[] }`, in plain words, with status `400` (bad input, or the job moved on since you opened it), `403` (refused), `404` (no such thing), or `409` (no profile yet: run `satyaapply setup`).
- Times are ISO 8601 strings in UTC. The app shows them in local time.
- Text from job posts and forms comes back as plain strings. The app renders it as text, never as HTML.
- Links come back only when they are `http` or `https`; otherwise the field is `null`.
- Numbers must be JSON whole numbers and switches must be `true` or `false`. `"5"` or `1` for a switch is refused.

## Shapes

```ts
type Status = "new" | "skipped" | "scored" | "ready" | "approved" | "dismissed" | "submitting"
  | "applied" | "unconfirmed" | "needs_input" | "external" | "failed" | "closed" | "finish";

type Group = "found" | "waiting_score" | "duplicate" | "no_ai" | "not_a_fit" | "skipped" | "wrong_title" | "wrong_place" | "too_old" | "skipped_company"
  | "scored" | "closed" | "needs_input" | "finish" | "failed" | "external" | "ready"
  | "auto_sent" | "approved" | "dismissed" | "applied" | "unconfirmed";

type JobRow = {
  id: number; title: string; company: string; location: string;
  score: number | null; status: Status; source: string; autoSubmitted: boolean;
  updatedAt: string;
};

type Sent = { question: string; answer: string; editable: boolean };
type OpenQuestion = { question: string; label: string };
type Action = "approve" | "answers" | "dismiss" | "thumbs" | "questions" | "retry"
  | "finished" | "revert";

type JobDetail = JobRow & {
  reason: string; note: string; source: string;
  url: string | null; applyUrl: string | null; description: string;
  sent: Sent[]; questions: OpenQuestion[]; changes: string[] | null;
  hasScreenshot: boolean; hasResume: boolean;
  feedback: -1 | 0 | 1; actions: Action[]; dismissReasons: string[];
};

type RunLog = {
  name: string; finishedAt: string; kind: "automatic" | "manual" | null;
  running: boolean; outcome: "done" | "failed" | "stopped" | null;
};
type RunState = {
  running: boolean; startedAt: string | null; exitCode: number | null;
  log: string[]; stoppable: boolean; stage: "find" | "score" | "tailor" | null; logs: RunLog[]; nextAutomatic: string | null; limits: { min: number; max: number; default: number };
};
type Summary = {
  total: number; counts: Partial<Record<Status, number>>;
  sites: { source: string; total: number; counts: Partial<Record<Status, number>> }[];
  run: RunState; suggestions: number;
};

type Sort = "updated" | "score" | "title" | "company" | "location";
type JobList = {
  jobs: JobRow[]; total: number; page: number; pageSize: number;
  dismissable: Status[]; dismissReasons: string[];
};

type Column = { status: Status; total: number; jobs: JobRow[] };

type Rule = { id: number; text: string };
type SavedAnswer = { question: string; answer: string; source: "user" | "ai" };
type Suggestion = { id: number; word: string };
type Learned = { rules: Rule[]; notes: Rule[]; answers: SavedAnswer[]; suggestions: Suggestion[] };

type SettingsValues = {
  name: string; email: string; phone: string; city: string; country: string; links: string[];
  currentCompany: string; yearsExperience: number;
  roles: string[]; titleKeywords: string[]; titleExclude: string[]; skipCompanies: string[];
  relocateCities: string[]; maxJobAgeDays: number; wellfound: boolean;
  wellfoundRoles: string[]; wellfoundTitles: string[]; wellfoundSkip: string[]; minScore: number;
  onsiteCity: boolean; remoteCountry: boolean; relocate: boolean; remoteAbroad: boolean;
  currency: string; expectedMin: number; expectedMax: number; currentSalary: number | null;
  noticePeriod: string; citizenship: string; workWithoutVisa: string[]; needsSponsorship: boolean;
  dateOfBirth: string; gender: string; disability: string; veteran: string; ethnicity: string;
  extraFacts: string; unknownQuestions: "skip" | "guess"; coverLetter: "required" | "always" | "never";
  companySearch: "off" | "daily" | "weekly"; autoSubmit: boolean; autoSubmitScore: number;
  jobsPerRun: number; scoresPerRun: number; dailyCap: number | null; linkedinCap: number;
  aiCallsPerDay: number; runEveryMinutes: number; summaryHour: number;
};
type SettingsLimits = {
  maxItems: number; maxText: number; maxLongText: number;
  numbers: Record<string, { min: number; max: number }>;
};
type Automatic = { supported: boolean; on: boolean; everyMinutes: number | null };
type SettingsView = {
  values: SettingsValues; limits: SettingsLimits; automatic: Automatic;
  resume: { format: "latex" | "structured" }; extension: { folder: string; built: boolean };
};
```

`actions` lists only what the job's status allows, so the app shows only those buttons. `revert` appears only when the job has a tailored resume. `changes` is `null` when the job wasn't tailored.

## Endpoints

### Jobs

| Method and path | Body | Answer |
|---|---|---|
| `GET /api/summary` | | `Summary` |
| `GET /api/jobs` | | `JobList`: one page of 50, newest first. Skipped and closed jobs are left out unless you ask for a status, a group or `show=all`. `total` counts every match. |
| `GET /api/new-jobs` | `?jobs=<ISO>&wellfound=<ISO>` | `{ jobs?: number, wellfound?: number }`: for each tab you name, the jobs found after that time that aren't skipped or closed (`jobs` is Career jobs). The sidebar sends when you last opened each tab, kept in this browser, and shows the counts as badges. |
| `GET /api/jobs?show=all` | | the same, skipped jobs included. Skipped also holds software jobs outside your titles, places or age (`note` says which: "not one of your titles", "not a place you work in", "posted too long ago" or "a company you skip"; no description). Each run updates the note, and the job goes back to `new` once it fits. The `skipped` group counts them all; `wrong_title`, `wrong_place`, `too_old` and `skipped_company` count each reason. |
| `GET /api/jobs?status=<Status>` | | the same, for one status |
| `GET /api/jobs?group=<Group>` | | the same, for one workflow box |
| `GET /api/workflow` | | `{ groups: Record<Group, number>, lastRun: { startedAt, groups: Record<Group, number> } \| null }`: the count in each workflow box, and how many jobs reached each box since the latest run started (`found` by when it was found, the rest by their last status change). `stage` in `RunState` is the step a run is on, read from its latest progress line. |
| `GET /api/board` | | Home's job lists. `{ columns: Column[], dismissReasons }`: scored, needs_input, finish, ready, approved, applied (the order jobs move in), the newest 8 jobs in each |
| `GET /api/jobs/<id>` | | `JobDetail` |

`GET /api/jobs` also takes, in any mix:

- `q`: words in the title or company. `company` and `location`: words in that field. Each is at most 100 characters; `%` and `_` are plain text.
- `minScore`: 1 to 100, only jobs scored at least that.
- `source`: one site (`career_pages`, `linkedin`, `naukri`, `indeed`, `wellfound`, `manual`). Without it, listed-only sites (Wellfound) are left out, here and in `counts`, the board and the workflow map. `sites` in `Summary` gives each listed-only site that's switched on its own counts, for its own tab.
- `sort`: one of `Sort` (default `updated`), and `order`: `asc` or `desc` (default newest or highest first, A to Z for text). Jobs with no score sort last either way.
- `page`: 1 or more. A page past the end returns the last page, and `page` in the answer says which.

An unknown status, group, sort, order, page or score is `400`. `dismissable` lists the statuses a job can be dismissed from, so the app only offers a checkbox on those rows.

A workflow box's count and its job list come from the same SQL condition (`store/groups.py`), so they always match.

### Job actions

Each one answers with the updated `JobDetail`, and is refused with `400` if the job's status no longer allows it.

| Method and path | Body | What it does |
|---|---|---|
| `POST /api/jobs/<id>/approve` | `{}` | `ready` → `approved`. Counts as a clean approval unless you edited an answer. |
| `POST /api/jobs/<id>/answers` | `{ answers: [{ question, answer }] }` | Changes filled-in answers before you approve. Changed answers become your saved answers. File uploads can't be changed. |
| `POST /api/jobs/<id>/dismiss` | `{ reason }`, one of `dismissReasons` | → `dismissed`. It's never applied to. |
| `POST /api/jobs/<id>/thumbs` | `{ value: 1 \| -1 }` | Good or bad match. A 👎 resets the trust count. |
| `POST /api/jobs/<id>/questions` | `{ answers: [{ question, answer }] }` | Answers the questions it couldn't. `needs_input` → `scored`, filled in on the next run. |
| `POST /api/jobs/<id>/retry` | `{}` | `needs_input` → `scored`, when its questions were answered on another job |
| `POST /api/jobs/<id>/finished` | `{}` | `finish` → `applied`, after you sent it yourself |
| `POST /api/jobs/<id>/revert` | `{}` | This job uses your original resume. The app then asks for a tailoring note. |
| `POST /api/jobs/<id>/handoff` | `{}` | For `finish` and `ready`. Opens the job as a tab in the filled-in browser (starting `satyaapply finish` in the background if it isn't open), filled in and stopped before Submit, and brings its tab to the front. Answers with `JobDetail`. When the site confirms, the job becomes `applied`. |
| `POST /api/jobs/<id>/score` | `{}` | `JobDetail`. Starts a score-only run for a new or skipped job; a job saved without its description has it read from its job board first. If a run is going, it waits its turn. |
| `POST /api/jobs/score` | `{ ids }` | `{ scoring, skipped }`. The same for several jobs; `JobList.scoring` lists the ids being scored or waiting. |
| `POST /api/jobs/dismiss` | `{ ids: number[], reason }`, 1 to 200 ids, `reason` one of `dismissReasons` | Dismisses many at once, the same way as one by one, and answers `{ dismissed, skipped }`. Jobs that moved on to a status you can't dismiss from are skipped. |


### Companies

| Method and path | Body | Answer |
|---|---|---|
| `POST /api/boards/link` | `{ link }`, a Greenhouse, Lever or Ashby job or careers link | `{ company, open, kept, added, gone }`. The company's board is saved and checked now and on every run. The linked job is kept even if your filters would skip it. Any other link is `400`. |

### What it learned

Each one answers with the updated `Learned`.

| Method and path | Body | What it does |
|---|---|---|
| `GET /api/learned` | | `Learned` |
| `POST /api/rules` | `{ kind: "rule" \| "tailoring_note", text }` | Adds a rule (changes scoring) or a tailoring note (changes tailoring). 1 to 300 characters. |
| `POST /api/rules/<id>/edit` | `{ text }` | Changes a rule or note |
| `POST /api/rules/<id>/delete` | `{}` | Deletes a rule or note |
| `POST /api/answers/edit` | `{ question, answer }` | Changes a saved answer. It becomes yours. |
| `POST /api/answers/delete` | `{ question }` | Forgets a saved answer. The next form that asks waits for you. |
| `POST /api/suggestions/<id>/accept` | `{}` | Adds the word to the titles to skip in your profile |
| `POST /api/suggestions/<id>/dismiss` | `{}` | Drops the suggestion. Nothing changes. |

### Runs and settings

| Method and path | Body | Answer |
|---|---|---|
| `GET /api/companies` | | `{ companies: { key, company, site, url, origin: "shared" \| "search" \| "link", addedAt, checkedAt, closed, jobs }[], search: { every, last, next } }`. `jobs` counts that company's listed jobs that aren't skipped or closed. |
| `POST /api/companies/find` | `{}` | `RunState`: starts a run that searches the web for new companies now, whatever **companySearch** says. `400` if a run is going. |
| `GET /api/runs` | | `RunState` |
| `POST /api/runs/start` | `{ limit, search, only? }` | `RunState`. `only` (`find`, `score` or `tailor`) runs just that step, as `satyaapply run --only`. `limit` is kept between 1 and 50; the form starts at the saved `jobsPerRun`. Nothing is sent. `400` if one is already running. |
| `POST /api/runs/stop` | `{}` | `RunState` |
| `GET /api/runs/log/<name>` | | `RunLog & { lines: string[] }`, the last 200 lines |
| `GET /api/settings` | | `SettingsView` |
| `POST /api/settings` | `SettingsValues` | `SettingsView`, or `400 { error, problems }` naming every problem at once. Nothing is saved unless all of it is valid. Moves a running schedule when `runEveryMinutes` changes. |
| `POST /api/settings/resume` | `{ name, data }`, `data` in base64, up to 5 MB | `{ format, pages }`. A `.tex` keeps its design when pdflatex is installed; other files are moved into the built-in design by Claude. The master PDF is rebuilt before the profile switches, so a resume that fails to build changes nothing. |
| `POST /api/settings/automatic` | `{ on: boolean }` | `Automatic`. Turns the background run on (every `runEveryMinutes`) or off. macOS only. |

### Chrome extension

| Request | Body | Answer |
|---|---|---|
| `POST /api/extension/job` | `{ url }` | `{ job }` for the page's job, or `null` |
| `POST /api/extension/add` | `{ url, posting?, text }` | `{ job, preparing }` |
| `POST /api/extension/jobs/<id>/answers` | `{ fields, ai }` | `{ answers, forYou, waiting, note }` |
| `POST /api/extension/jobs/<id>/applied` | `{ sent }` | `{ applied: true }`; a job that auto-submit pressed Submit on is marked auto-submitted |
| `POST /api/extension/send/next` | `{}` | `{ job: { id, url } \| null }`: the next job to auto-submit, only while **autoSubmit** is on, no run is going and no other send is in progress. Each job is handed out once |
| `POST /api/extension/jobs/<id>/submitting` | `{}` | `{ go }`: written before Submit is pressed; `false` if auto-submit was turned off or the job was already tried |
| `POST /api/autosend/queue` | `{}` | `{ queued, below, score }`: **Send these with auto-submit** on Home. Queues every ready career-page job scoring `autoSubmitScore` or more for sending, even jobs tailored before it was turned on and even during a run. `400` while auto-submit is off |
| `POST /api/extension/jobs/<id>/held` | `{ why }` | `{ held: true }`: auto-submit stopped; the reason goes in the job's note |

## Files and pages

- `GET /jobs/<id>/screenshot.png` and `GET /jobs/<id>/resume.pdf` serve a job's files. They're looked up by job id, never by a path in the address, and only from inside the data folder.
- `GET /assets/<name>` serves the app's built files.
- Every other `GET` returns the app's `index.html`, so links like `/jobs/12` work after a reload. If the app isn't built, it's `503` with the build command.

## Headers

Every answer has `Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'`, plus `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer`.

`Cache-Control` is `no-store`, except for `/assets/*`, which is `public, max-age=31536000, immutable` because those file names change with every build.
