import type { SettingsValues } from "../../api/types";

const NUMBERS = [
  "yearsExperience",
  "maxJobAgeDays",
  "minScore",
  "expectedMin",
  "expectedMax",
  "jobsPerRun",
  "scoresPerRun",
  "linkedinCap",
  "aiCallsPerDay",
  "runEveryMinutes",
  "summaryHour",
  "linkedinReadsPerDay",
] as const;
const OPTIONAL_NUMBERS = ["currentSalary", "dailyCap"] as const;

export type NumberName = (typeof NUMBERS)[number] | (typeof OPTIONAL_NUMBERS)[number];
export type Draft = Omit<SettingsValues, NumberName> & Record<NumberName, string>;

export function toDraft(values: SettingsValues): Draft {
  const draft: Record<string, unknown> = { ...values };
  for (const name of [...NUMBERS, ...OPTIONAL_NUMBERS]) {
    const value = values[name];
    draft[name] = value === null ? "" : String(value);
  }
  return draft as Draft;
}

export function toValues(draft: Draft): SettingsValues {
  const values: Record<string, unknown> = { ...draft };
  for (const name of NUMBERS) {
    values[name] = draft[name].trim() ? Number(draft[name]) : Number.NaN;
  }
  for (const name of OPTIONAL_NUMBERS) {
    values[name] = draft[name].trim() ? Number(draft[name]) : null;
  }
  return values as SettingsValues;
}
