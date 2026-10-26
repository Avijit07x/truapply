import type { Status } from "../api/types";

export type Tone = "good" | "warn" | "bad" | "plain";

export const STATUS: Record<Status, { label: string; tone: Tone }> = {
  new: { label: "Waiting to be scored", tone: "plain" },
  skipped: { label: "Skipped", tone: "plain" },
  scored: { label: "Good match, not filled yet", tone: "good" },
  ready: { label: "Filled, waiting for your OK", tone: "good" },
  approved: { label: "Approved, sends on the next run", tone: "good" },
  dismissed: { label: "Dismissed", tone: "plain" },
  submitting: { label: "Sending", tone: "plain" },
  applied: { label: "Applied", tone: "good" },
  unconfirmed: { label: "Sent, not confirmed", tone: "warn" },
  needs_input: { label: "Needs your answer", tone: "warn" },
  external: { label: "Apply on their site", tone: "warn" },
  failed: { label: "Something broke", tone: "bad" },
  closed: { label: "Job closed", tone: "plain" },
  finish: { label: "Finish it yourself", tone: "warn" },
};

export const STATUSES = Object.keys(STATUS) as Status[];

export function isStatus(value: string | null): value is Status {
  return value !== null && value in STATUS;
}
