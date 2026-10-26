import type { Group } from "../../api/types";

export type StepKind = "auto" | "question" | "jobs" | "done";

export type Step = {
  id: string;
  kind: StepKind;
  title: string;
  note?: string;
  group?: Group;
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
  { id: "lane-fill", title: "2 · Fill the form", x: lane(1), height: 564, exitY: 540 },
  { id: "lane-send", title: "3 · Send", x: lane(2), height: 700 },
];

export const STEPS: readonly Step[] = [
  step(0, row(0), {
    id: "find",
    kind: "auto",
    title: "Finds jobs on career pages",
    note: "Skips unwanted titles and places",
    group: "found",
    countLabel: "found",
  }),
  step(0, row(1), { id: "seen", kind: "question", title: "Seen it before?" }),
  step(0, row(2), {
    id: "score",
    kind: "auto",
    title: "AI scores each job",
    note: "Against your resume and rules",
    group: "waiting_score",
    countLabel: "waiting",
  }),
  step(0, row(3), { id: "fit", kind: "question", title: "A fit for you?" }),
  step(1, row(0), { id: "scored", kind: "jobs", title: "Good matches", group: "scored" }),
  step(1, row(1), {
    id: "fill",
    kind: "auto",
    title: "Tailors resume, fills the form",
    note: "Fact-checked, never guesses",
  }),
  step(1, row(2), { id: "worked", kind: "question", title: "Did the form work?" }),
  step(1, 432, { id: "needs", kind: "question", title: "Needs you to step in?" }),
  step(2, row(0), {
    id: "earned",
    kind: "question",
    title: "Auto-submit earned?",
    note: "Strong matches only",
  }),
  step(2, row(1), { id: "ready", kind: "jobs", title: "Waiting for your OK", group: "ready" }),
  step(2, row(2), { id: "approve", kind: "question", title: "Do you approve it?" }),
  step(2, row(3), {
    id: "approved",
    kind: "jobs",
    title: "Approved",
    note: "Sent on a run with Really send",
    group: "approved",
  }),
  step(2, row(4), { id: "confirmed", kind: "question", title: "Did the site confirm it?" }),
  step(2, row(5), { id: "applied", kind: "done", title: "Applied", group: "applied" }),
];

export const OUTCOMES: readonly Outcome[] = [
  outcome(0, 68, "skipped_other", "Skipped", "Other reason"),
  outcome(0, 170, "duplicate", "Yes", "Duplicates"),
  outcome(0, 364, "no_ai", "No", "Bans AI help"),
  outcome(0, 424, "not_a_fit", "No", "Not a fit"),
  outcome(1, 224, "closed", "Gone", "Job closed"),
  outcome(1, 282, "failed", "Error", "Something broke"),
  outcome(1, 340, "external", "Unsupported", "Apply on their site"),
  outcome(1, 408, "needs_input", "A question", "Needs your answer"),
  outcome(1, 468, "finish", "Picture check", "Finish these"),
  outcome(2, 68, "auto_sent", "Yes", "Sent automatically"),
  outcome(2, 282, "dismissed", "No", "Dismissed"),
  outcome(2, 506, "unconfirmed", "No", "Not confirmed"),
];

export const LINKS: readonly Link[] = [
  { from: "find", to: "seen", kind: "spine" },
  { from: "find", to: "o-skipped_other", kind: "branch" },
  { from: "seen", to: "score", label: "No", kind: "spine" },
  { from: "seen", to: "o-duplicate", kind: "branch" },
  { from: "score", to: "fit", kind: "spine" },
  { from: "fit", to: "o-no_ai", kind: "branch" },
  { from: "fit", to: "o-not_a_fit", kind: "branch" },
  { from: "fit", to: "scored", label: "Yes", kind: "lane" },
  { from: "scored", to: "fill", kind: "spine" },
  { from: "fill", to: "worked", kind: "spine" },
  { from: "worked", to: "o-closed", kind: "branch" },
  { from: "worked", to: "o-failed", kind: "branch" },
  { from: "worked", to: "o-external", kind: "branch" },
  { from: "worked", to: "needs", label: "Yes", kind: "spine" },
  { from: "needs", to: "o-needs_input", kind: "branch" },
  { from: "needs", to: "o-finish", kind: "branch" },
  { from: "needs", to: "earned", label: "No", kind: "lane" },
  { from: "earned", to: "o-auto_sent", kind: "branch" },
  { from: "earned", to: "ready", label: "No", kind: "spine" },
  { from: "ready", to: "approve", kind: "spine" },
  { from: "approve", to: "o-dismissed", kind: "branch" },
  { from: "approve", to: "approved", label: "Yes", kind: "spine" },
  { from: "approved", to: "confirmed", kind: "spine", automatic: true },
  { from: "confirmed", to: "o-unconfirmed", kind: "branch" },
  { from: "confirmed", to: "applied", label: "Yes", kind: "spine" },
];

export const EXPLAIN: Record<Group, string> = {
  found: "Every job saved from the career pages it checks.",
  waiting_score: "Saved jobs the AI hasn't scored yet. They're scored on the next run.",
  skipped_other: "Skipped for another reason, such as a place you don't work in.",
  duplicate: "The same job seen again on another board or posting.",
  no_ai: "The employer doesn't accept AI-assisted applications, so it's left alone.",
  not_a_fit: "Scored below your minimum, or it has a deal-breaker.",
  scored: "Good matches. The next run tailors your resume and fills their forms.",
  closed: "The job was removed from the company's board.",
  failed: "Something broke while filling the form. Open a job to see the last step.",
  external: "A site it can't fill. Apply on their site yourself.",
  needs_input: "A legal or eligibility question it never guesses. Answer once and it's reused.",
  finish: "Filled, but the site shows a picture check. Finish it in your own browser.",
  auto_sent: "Sent for you, because auto-submit is on and it was a strong match.",
  ready: "Filled and waiting for your OK. Approve or dismiss each one.",
  dismissed: "Jobs you said no to. Your reasons help it suggest what to skip.",
  approved: "Approved by you. Sent on the next run where you tick Really send.",
  unconfirmed: "Sent, but the site didn't show a confirmation. Check your email.",
  applied: "Sent and confirmed.",
};
