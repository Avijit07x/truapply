export type Status = "new" | "skipped" | "scored" | "ready" | "dismissed" | "applied" | "closed";

export type Group =
  | "found"
  | "waiting_score"
  | "duplicate"
  | "no_ai"
  | "not_a_fit"
  | "skipped"
  | "wrong_title"
  | "wrong_place"
  | "too_old"
  | "skipped_company"
  | "scored"
  | "closed"
  | "ready"
  | "dismissed"
  | "applied";

export type JobRow = {
  id: number;
  title: string;
  company: string;
  location: string;
  score: number | null;
  status: Status;
  source: string;
  autoSubmitted: boolean;
  updatedAt: string;
};

export type Sent = { question: string; answer: string };
export type Action = "dismiss" | "thumbs" | "finished" | "revert" | "score" | "tailor";
export type Thumbs = -1 | 0 | 1;

export type JobDetail = JobRow & {
  reason: string;
  note: string;
  source: string;
  url: string | null;
  applyUrl: string | null;
  description: string;
  sent: Sent[];
  changes: string[] | null;
  hasResume: boolean;
  feedback: Thumbs;
  actions: Action[];
  dismissReasons: string[];
};

export type Sort = "updated" | "score" | "title" | "company" | "location";
export type Order = "asc" | "desc";
export type JobQuery = {
  show?: "all";
  status?: Status;
  group?: Group;
  q?: string;
  sort?: Sort;
  order?: Order;
  page?: number;
  company?: string;
  location?: string;
  minScore?: number;
  source?: string;
};
export type JobList = {
  jobs: JobRow[];
  total: number;
  page: number;
  pageSize: number;
  dismissable: Status[];
  scorable: Status[];
  scoring: number[];
  dismissReasons: string[];
};
export type Dismissed = { dismissed: number; skipped: number };
export type Scoring = { scoring: number; skipped: number };
export type Linked = { company: string; open: number; kept: number; added: number; gone: boolean };
export type Column = { status: Status; total: number; jobs: JobRow[] };
export type Board = { columns: Column[]; dismissReasons: string[] };
export type Workflow = {
  groups: Record<Group, number>;
  lastRun: { startedAt: string; groups: Record<Group, number> } | null;
};

export type RunKind = "automatic" | "manual";
export type RunLog = {
  name: string;
  finishedAt: string;
  kind: RunKind | null;
  running: boolean;
  outcome: "done" | "failed" | "stopped" | null;
};
export type RunLimits = { min: number; max: number; default: number };
export type RunState = {
  running: boolean;
  startedAt: string | null;
  exitCode: number | null;
  log: string[];
  stoppable: boolean;
  stage: RunStage | null;
  logs: RunLog[];
  nextAutomatic: string | null;
  limits: RunLimits;
};
export type RunLogLines = Omit<RunLog, "running" | "outcome"> & { lines: string[] };
export type RunStage = "find" | "score" | "tailor";
export type RunChoice = { limit: number; search: boolean; only?: RunStage };

export type SiteSummary = {
  source: string;
  total: number;
  counts: Partial<Record<Status, number>>;
};
export type Summary = {
  total: number;
  counts: Partial<Record<Status, number>>;
  sites: SiteSummary[];
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

export type CompanySearch = "off" | "daily" | "weekly";
export type CompanyOrigin = "shared" | "search" | "link";
export type CompanyRow = {
  key: string;
  company: string;
  site: "greenhouse" | "lever" | "ashby";
  url: string;
  origin: CompanyOrigin;
  addedAt: string;
  checkedAt: string | null;
  closed: boolean;
  jobs: number;
};
export type Companies = {
  companies: CompanyRow[];
  search: { every: CompanySearch; last: string | null; next: string | null };
};
export type SendQueued = { queued: number; below: number; score: number };
export type SettingsValues = {
  name: string;
  email: string;
  phone: string;
  city: string;
  country: string;
  links: string[];
  currentCompany: string;
  yearsExperience: number;
  roles: string[];
  titleKeywords: string[];
  titleExclude: string[];
  skipCompanies: string[];
  relocateCities: string[];
  maxJobAgeDays: number;
  wellfound: boolean;
  wellfoundRoles: string[];
  wellfoundTitles: string[];
  wellfoundSkip: string[];
  minScore: number;
  onsiteCity: boolean;
  remoteCountry: boolean;
  relocate: boolean;
  remoteAbroad: boolean;
  currency: string;
  expectedMin: number;
  expectedMax: number;
  currentSalary: number | null;
  noticePeriod: string;
  citizenship: string;
  workWithoutVisa: string[];
  needsSponsorship: boolean;
  dateOfBirth: string;
  gender: string;
  disability: string;
  veteran: string;
  ethnicity: string;
  extraFacts: string;
  unknownQuestions: "skip" | "guess";
  coverLetter: "required" | "always" | "never";
  companySearch: CompanySearch;
  autoSubmit: boolean;
  autoSubmitScore: number;
  jobsPerRun: number;
  scoresPerRun: number;
  dailyCap: number | null;
  linkedinCap: number;
  aiCallsPerDay: number;
  runEveryMinutes: number;
  summaryHour: number;
};
export type NumberLimit = { min: number; max: number };
export type SettingsLimits = {
  maxItems: number;
  maxText: number;
  maxLongText: number;
  numbers: Record<string, NumberLimit>;
};
export type Automatic = { supported: boolean; on: boolean; everyMinutes: number | null };
export type Extension = { folder: string; built: boolean };
export type ResumeFormat = "latex" | "structured";
export type ResumeInfo = { format: ResumeFormat };
export type ResumeReplaced = { format: ResumeFormat; pages: number };
export type ResumeUpload = { name: string; data: string };
export type SettingsView = {
  values: SettingsValues;
  limits: SettingsLimits;
  automatic: Automatic;
  resume: ResumeInfo;
  extension: Extension;
};

export type ApiError = { error: string; problems?: string[] };
