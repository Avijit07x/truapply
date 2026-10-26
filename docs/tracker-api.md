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

type Group = "found" | "waiting_score" | "duplicate" | "no_ai" | "not_a_fit" | "skipped_other"
  | "scored" | "closed" | "needs_input" | "finish" | "failed" | "external" | "ready"
  | "auto_sent" | "approved" | "dismissed" | "applied" | "unconfirmed";

type JobRow = {
  id: number; title: string; company: string; location: string;
  score: number | null; status: Status; updatedAt: string;
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

type Trust = { count: number; offerAt: number; autoSubmit: boolean; autoSubmitScore: number };
type RunLog = { name: string; finishedAt: string };
type RunState = {
  running: boolean; startedAt: string | null; exitCode: number | null;
  log: string[]; logs: RunLog[]; limits: { min: number; max: number; default: number };
};
type Summary = {
  total: number; counts: Partial<Record<Status, number>>;
  trust: Trust; run: RunState; suggestions: number;
};

type Column = { status: Status; total: number; jobs: JobRow[] };

type Rule = { id: number; text: string };
type SavedAnswer = { question: string; answer: string; source: "user" | "ai" };
type Suggestion = { id: number; word: string };
type Learned = { rules: Rule[]; notes: Rule[]; answers: SavedAnswer[]; suggestions: Suggestion[] };

type SettingsValues = {
  titleKeywords: string[]; titleExclude: string[]; skipCompanies: string[];
  relocateCities: string[]; maxJobAgeDays: number; minScore: number;
  expectedMin: number; expectedMax: number; noticePeriod: string; dailyCap: number | null;
  onsiteCity: boolean; remoteCountry: boolean; relocate: boolean; remoteAbroad: boolean;
};
type SettingsFixed = {
  city: string; country: string; currency: string; strongScore: number; linkedinCap: number;
  maxItems: number; maxText: number; maxJobAgeDays: number; maxDailyCap: number;
};
type SettingsView = { values: SettingsValues; fixed: SettingsFixed };
```

`actions` lists only what the job's status allows, so the app shows only those buttons. `revert` appears only when the job has a tailored resume. `changes` is `null` when the job wasn't tailored.

## Endpoints

### Jobs

| Method and path | Body | Answer |
|---|---|---|
| `GET /api/summary` | | `Summary` |
| `GET /api/jobs` | | `{ jobs: JobRow[], total }`: newest first, at most 500. `total` counts every match. |
| `GET /api/jobs?status=<Status>` | | the same, for one status |
| `GET /api/jobs?group=<Group>` | | the same, for one workflow box. An unknown status or group is `400`. |
| `GET /api/workflow` | | `{ groups: Record<Group, number> }`: the count in each workflow box |
| `GET /api/board` | | `{ columns: Column[], dismissReasons }`: needs_input, finish, ready, approved, applied, scored, the newest 8 jobs in each |
| `GET /api/jobs/<id>` | | `JobDetail` |

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

The board's drag and drop uses `approve` and `dismiss`, so a drag does exactly what the job page buttons do.

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

### Auto-submit, runs and settings

| Method and path | Body | Answer |
|---|---|---|
| `POST /api/auto-submit` | `{ on: boolean }` | `Trust`. Turning it on before `offerAt` clean approvals is `400`. |
| `GET /api/runs` | | `RunState` |
| `POST /api/runs/start` | `{ limit, search, send }` | `RunState`. `limit` is kept between 1 and 20. `send: false` is a dry run. `400` if one is already running. |
| `POST /api/runs/stop` | `{}` | `RunState` |
| `GET /api/runs/log/<name>` | | `RunLog & { lines: string[] }`, the last 200 lines |
| `GET /api/settings` | | `SettingsView` |
| `POST /api/settings` | `SettingsValues` | `SettingsView`, or `400 { error, problems }` naming every problem at once. Nothing is saved unless all of it is valid. |

## Files and pages

- `GET /jobs/<id>/screenshot.png` and `GET /jobs/<id>/resume.pdf` serve a job's files. They're looked up by job id, never by a path in the address, and only from inside the data folder.
- `GET /assets/<name>` serves the app's built files.
- Every other `GET` returns the app's `index.html`, so links like `/jobs/12` work after a reload. If the app isn't built, it's `503` with the build command.

## Headers

Every answer has `Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'`, plus `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer`.

`Cache-Control` is `no-store`, except for `/assets/*`, which is `public, max-age=31536000, immutable` because those file names change with every build.
