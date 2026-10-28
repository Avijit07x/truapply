import type { Group } from "../api/types";
import type { Tone } from "./status";

export const GROUP_LABEL: Record<Group, string> = {
  found: "Every job it found",
  waiting_score: "Waiting to be scored",
  duplicate: "Duplicates",
  no_ai: "Employer bans AI help",
  not_a_fit: "Not a fit: low score or deal-breaker",
  skipped: "Skipped before scoring",
  wrong_title: "Not one of your titles",
  wrong_place: "Not a place you work in",
  too_old: "Posted too long ago",
  skipped_company: "A company you skip",
  scored: "Good matches, not tailored yet",
  closed: "Job closed",
  ready: "Ready for you to apply",
  dismissed: "Dismissed",
  applied: "Applied",
};

export function isGroup(value: string | null): value is Group {
  return value !== null && value in GROUP_LABEL;
}

export const GROUP_TONE: Partial<Record<Group, Tone>> = {
  ready: "good",
  scored: "good",
  applied: "good",
};
