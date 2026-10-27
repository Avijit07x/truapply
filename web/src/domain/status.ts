import type { Status } from "../api/types";

export type Tone = "good" | "warn" | "bad" | "plain";

export const STATUS: Record<Status, { label: string; tone: Tone }> = {
  new: { label: "Waiting to be scored", tone: "plain" },
  skipped: { label: "Skipped", tone: "plain" },
  scored: { label: "Good match, not tailored yet", tone: "good" },
  ready: { label: "Ready for you to apply", tone: "good" },
  dismissed: { label: "Dismissed", tone: "plain" },
  applied: { label: "Applied", tone: "good" },
  closed: { label: "Job closed", tone: "plain" },
};

export const STATUSES = Object.keys(STATUS) as Status[];

export function isStatus(value: string | null): value is Status {
  return value !== null && value in STATUS;
}

export const activeCount = (counts: Partial<Record<Status, number>>, total: number) =>
  total - (counts.skipped ?? 0) - (counts.closed ?? 0);
