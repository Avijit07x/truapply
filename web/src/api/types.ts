export type Status =
  | "new"
  | "skipped"
  | "scored"
  | "ready"
  | "approved"
  | "dismissed"
  | "submitting"
  | "applied"
  | "unconfirmed"
  | "needs_input"
  | "external"
  | "failed"
  | "closed"
  | "finish";

export type Group =
  | "found"
  | "waiting_score"
  | "duplicate"
  | "no_ai"
  | "not_a_fit"
  | "skipped_other"
  | "scored"
  | "closed"
  | "needs_input"
  | "finish"
  | "failed"
  | "external"
  | "ready"
  | "auto_sent"
  | "approved"
  | "dismissed"
  | "applied"
  | "unconfirmed";

export type JobRow = {
  id: number;
  title: string;
  company: string;
  location: string;
  score: number | null;
  status: Status;
  updatedAt: string;
};

export type Sent = { question: string; answer: string; editable: boolean };
export type OpenQuestion = { question: string; label: string };
export type Action =
  "approve" | "answers" | "dismiss" | "thumbs" | "questions" | "retry" | "finished" | "revert";
export type Thumbs = -1 | 0 | 1;

export type JobDetail = JobRow & {
  reason: string;
  note: string;
  source: string;
  url: string | null;
  applyUrl: string | null;
  description: string;
  sent: Sent[];
  questions: OpenQuestion[];
  changes: string[] | null;
  hasScreenshot: boolean;
  hasResume: boolean;
  feedback: Thumbs;
  actions: Action[];
  dismissReasons: string[];
};

export type JobFilter = { status?: Status; group?: Group };
export type JobList = { jobs: JobRow[]; total: number };
export type Column = { status: Status; total: number; jobs: JobRow[] };
export type Board = { columns: Column[]; dismissReasons: string[] };
export type Workflow = { groups: Record<Group, number> };

export type Trust = {
  count: number;
  offerAt: number;
  autoSubmit: boolean;
  autoSubmitScore: number;
};
export type RunLog = { name: string; finishedAt: string };
export type RunLimits = { min: number; max: number; default: number };
export type RunState = {
  running: boolean;
  startedAt: string | null;
  exitCode: number | null;
  log: string[];
  logs: RunLog[];
  limits: RunLimits;
};
export type RunLogLines = RunLog & { lines: string[] };
export type RunChoice = { limit: number; search: boolean; send: boolean };

export type Summary = {
  total: number;
  counts: Partial<Record<Status, number>>;
  trust: Trust;
  run: RunState;
  suggestions: number;
};

export type Rule = { id: number; text: string };
export type RuleKind = "rule" | "tailoring_note";
export type SavedAnswer = { question: string; answer: string; source: "user" | "ai" };
export type Suggestion = { id: number; word: string };
export type Learned = {
  rules: Rule[];
  notes: Rule[];
  answers: SavedAnswer[];
  suggestions: Suggestion[];
};

export type SettingsValues = {
  titleKeywords: string[];
  titleExclude: string[];
  skipCompanies: string[];
  relocateCities: string[];
  maxJobAgeDays: number;
  minScore: number;
  expectedMin: number;
  expectedMax: number;
  noticePeriod: string;
  dailyCap: number | null;
  onsiteCity: boolean;
  remoteCountry: boolean;
  relocate: boolean;
  remoteAbroad: boolean;
};
export type SettingsFixed = {
  city: string;
  country: string;
  currency: string;
  strongScore: number;
  linkedinCap: number;
  maxItems: number;
  maxText: number;
  maxJobAgeDays: number;
  maxDailyCap: number;
};
export type SettingsView = { values: SettingsValues; fixed: SettingsFixed };

export type ApiError = { error: string; problems?: string[] };
