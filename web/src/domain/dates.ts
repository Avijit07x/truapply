import type { JobQuery } from "../api/types";

export const WHEN = ["today", "week", "month", "custom"] as const;
export type When = (typeof WHEN)[number];

const DAY = /^(\d{4})-(\d{2})-(\d{2})$/;

export function isWhen(value: string | null): value is When {
  return WHEN.some((when) => when === value);
}

export function isDay(value: string | null): value is string {
  return value !== null && DAY.test(value);
}

export function dayStart(day: string): Date {
  const [, year, month, date] = DAY.exec(day) ?? [];
  return new Date(Number(year), Number(month) - 1, Number(date));
}

export function dayOf(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${String(date.getFullYear())}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function nextDay(day: string): Date {
  const start = dayStart(day);
  start.setDate(start.getDate() + 1);
  return start;
}

function since(when: Exclude<When, "custom">, now: Date): Date {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (when === "week") {
    today.setDate(today.getDate() - ((today.getDay() + 6) % 7));
  }
  return when === "month" ? new Date(now.getFullYear(), now.getMonth(), 1) : today;
}

export function rangeOf(query: JobQuery, now = new Date()): Pick<JobQuery, "after" | "before"> {
  if (!query.when) {
    return {};
  }
  if (query.when !== "custom") {
    return { after: since(query.when, now).toISOString() };
  }
  return {
    after: query.from ? dayStart(query.from).toISOString() : undefined,
    before: query.to ? nextDay(query.to).toISOString() : undefined,
  };
}

export function apiOf(query: JobQuery): JobQuery {
  return { ...query, when: undefined, from: undefined, to: undefined, ...rangeOf(query) };
}
