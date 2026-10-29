import type { Group, RunStage } from "../../api/types";

export type StepKind = "auto" | "question" | "jobs" | "done";

export type Step = {
  id: string;
  kind: StepKind;
  title: string;
  note?: string;
  group?: Group;
  stage?: RunStage;
  countLabel?: string;
  x: number;
  y: number;
};

export type Outcome = {
  id: string;
  group: Group;
  branch: string;
  title: string;
  x: number;
  y: number;
};

export type Link = {
  from: string;
  to: string;
  label?: string;
  kind: "spine" | "branch" | "lane";
  automatic?: boolean;
};

export type Lane = { id: string; title: string; x: number; height: number; exitY?: number };

export const STEP_WIDTH = 224;
export const OUTCOME_WIDTH = 156;
export const LANE_WIDTH = 448;

const PITCH = 472;
const SPINE = 16;
const SIDE = 276;
const ROW = 112;
const TOP = 52;

function lane(index: number): number {
  return index * PITCH;
}

function row(index: number): number {
  return TOP + index * ROW;
}

function step(index: number, y: number, spec: Omit<Step, "x" | "y">): Step {
  return { ...spec, x: lane(index) + SPINE, y };
}

function outcome(index: number, y: number, group: Group, branch: string, title: string): Outcome {
  return { id: `o-${group}`, group, branch, title, x: lane(index) + SIDE, y };
}

export const LANES: readonly Lane[] = [
  { id: "lane-find", title: "1 · Find and score", x: lane(0), height: 524, exitY: 500 },
  { id: "lane-tailor", title: "2 · Tailor the resume", x: lane(1), height: 412, exitY: 388 },
  { id: "lane-apply", title: "3 · You apply", x: lane(2), height: 364 },
];

export const STEPS: readonly Step[] = [
  step(0, row(0), {
    id: "find",
    kind: "auto",
    title: "Finds jobs on career pages",
    note: "Skips unwanted titles and places",
    group: "found",
    stage: "find",
    countLabel: "found",
  }),
  step(0, row(1), { id: "seen", kind: "question", title: "Seen it before?" }),
  step(0, row(2), {
    id: "score",
    kind: "auto",
    title: "AI scores each job",
    note: "Against your resume and rules",
    group: "waiting_score",
    stage: "score",
    countLabel: "waiting",
  }),
  step(0, row(3), { id: "fit", kind: "question", title: "A fit for you?" }),
  step(1, row(0), { id: "scored", kind: "jobs", title: "Good matches", group: "scored" }),
  step(1, row(1), {
    id: "tailor",
    kind: "auto",
    title: "Tailors your resume",
    note: "Fact-checked, never adds anything",
    stage: "tailor",
  }),
  step(1, row(2), { id: "open", kind: "question", title: "Still open?" }),
  step(2, row(0), {
    id: "ready",
    kind: "jobs",
    title: "Ready for you to apply",
    note: "Open it in your Chrome",
    group: "ready",
  }),
  step(2, row(1), { id: "apply", kind: "question", title: "Do you apply?" }),
  step(2, row(2), { id: "applied", kind: "done", title: "Applied", group: "applied" }),
];

export const OUTCOMES: readonly Outcome[] = [
  outcome(0, 68, "skipped", "Skipped", "Title, place or date"),
  outcome(0, 170, "duplicate", "Yes", "Duplicates"),
  outcome(0, 364, "no_ai", "No", "Bans AI help"),
  outcome(0, 424, "not_a_fit", "No", "Not a fit"),
  outcome(1, 282, "closed", "Gone", "Job closed"),
  outcome(2, 170, "dismissed", "No", "Dismissed"),
];

export const LINKS: readonly Link[] = [
  { from: "find", to: "seen", kind: "spine" },
  { from: "find", to: "o-skipped", kind: "branch" },
  { from: "seen", to: "score", label: "No", kind: "spine" },
  { from: "seen", to: "o-duplicate", kind: "branch" },
  { from: "score", to: "fit", kind: "spine" },
  { from: "fit", to: "o-no_ai", kind: "branch" },
  { from: "fit", to: "o-not_a_fit", kind: "branch" },
  { from: "fit", to: "scored", label: "Yes", kind: "lane" },
  { from: "scored", to: "tailor", kind: "spine" },
  { from: "tailor", to: "open", kind: "spine" },
  { from: "open", to: "o-closed", kind: "branch" },
  { from: "open", to: "ready", label: "Yes", kind: "lane" },
  { from: "ready", to: "apply", kind: "spine" },
  { from: "apply", to: "o-dismissed", kind: "branch" },
  { from: "apply", to: "applied", label: "Yes", kind: "spine" },
];

export const EXPLAIN: Record<Group, string> = {
  found: "Every job saved from the career pages it checks.",
  waiting_score: "Saved jobs the AI hasn't scored yet. They're scored on the next run.",
  skipped: "Saved but never scored, because it missed one of your Job search settings.",
  wrong_title: "The title isn't one of your title keywords, or it has a word you skip.",
  wrong_place: "It's in a place you don't work in, or remote where you don't want remote.",
  too_old: "Posted longer ago than the oldest job you want to consider.",
  skipped_company: "From a company on your list of companies to skip.",
  duplicate: "The same job seen again on another board or posting.",
  no_ai: "The employer doesn't accept AI-assisted applications, so it's left alone.",
  not_a_fit: "Scored below your minimum, or it has a deal-breaker.",
  scored: "Good matches. The next run tailors your resume for each one.",
  closed: "The job was removed from the company's board, or its deadline to apply passed.",
  ready:
    "Tailored and ready. Open one in your Chrome; the extension fills it in and you press Submit.",
  dismissed: "Jobs you said no to. Your reasons help it suggest what to skip.",
  applied: "Jobs you submitted.",
};

export type SettingsPart = "search" | "scoring" | "tailoring" | "applying";
export type StepPanel = { stage?: RunStage; settings: SettingsPart };

const SEARCH: StepPanel = { stage: "find", settings: "search" };
const SCORING: StepPanel = { stage: "score", settings: "scoring" };
const TAILORING: StepPanel = { stage: "tailor", settings: "tailoring" };
const APPLYING: StepPanel = { settings: "applying" };

export const PANELS: Readonly<Record<string, StepPanel>> = {
  find: SEARCH,
  seen: SEARCH,
  "o-skipped": SEARCH,
  "o-duplicate": SEARCH,
  score: SCORING,
  fit: SCORING,
  "o-no_ai": SCORING,
  "o-not_a_fit": SCORING,
  scored: TAILORING,
  tailor: TAILORING,
  open: TAILORING,
  "o-closed": TAILORING,
  ready: APPLYING,
  apply: APPLYING,
  applied: APPLYING,
  "o-dismissed": APPLYING,
};

export const RUN_LABEL: Record<RunStage, string> = {
  find: "Find new jobs now",
  score: "Score waiting jobs now",
  tailor: "Tailor good matches now",
};

export const STEP_EXPLAIN: Readonly<Record<string, string>> = {
  seen: "A job already in your list, or the same job on another board, is set aside.",
  fit: "The AI score is checked against your minimum match score, deal-breakers and employers that ban AI help.",
  tailor: "Your resume is rewritten for each good match, using only facts you gave it.",
  open: "Before tailoring, it checks the job is still on the company's board and its deadline to apply hasn't passed.",
  apply:
    "You open each ready job in your Chrome, check it and press Submit, or auto-submit sends it.",
};
