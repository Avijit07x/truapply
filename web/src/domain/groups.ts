import type { Group } from "../api/types";
import type { Tone } from "./status";

export const GROUP_LABEL: Record<Group, string> = {
  found: "Every job it found",
  waiting_score: "Waiting to be scored",
  duplicate: "Duplicates",
  no_ai: "Employer bans AI help",
  not_a_fit: "Not a fit: low score or deal-breaker",
  skipped_other: "Skipped, other reason",
  scored: "Good matches, not filled yet",
  closed: "Job closed",
  needs_input: "Needs your answer",
  finish: "Finish these",
  failed: "Something broke",
  external: "Apply on their site",
  ready: "Waiting for your OK",
  auto_sent: "Sent automatically",
  approved: "Approved",
  dismissed: "Dismissed",
  applied: "Applied",
  unconfirmed: "Sent, not confirmed",
};

export function isGroup(value: string | null): value is Group {
  return value !== null && value in GROUP_LABEL;
}

export const GROUP_TONE: Partial<Record<Group, Tone>> = {
  needs_input: "warn",
  finish: "warn",
  external: "warn",
  unconfirmed: "warn",
  failed: "bad",
  auto_sent: "good",
  approved: "good",
  ready: "good",
  scored: "good",
  applied: "good",
};
