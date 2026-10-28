import { type Clock, useClock } from "./clock";

const HOUR12: Record<Clock, boolean | undefined> = { system: undefined, "12": true, "24": false };
const moments = new Map<Clock, Intl.DateTimeFormat>();

function moment(clock: Clock): Intl.DateTimeFormat {
  const made =
    moments.get(clock) ??
    new Intl.DateTimeFormat(undefined, {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: HOUR12[clock],
    });
  moments.set(clock, made);
  return made;
}

export function when(iso: string | null): string {
  return iso ? moment(useClock.getState().clock).format(new Date(iso)) : "";
}

export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count.toLocaleString()} ${count === 1 ? one : many}`;
}

const relative = new Intl.RelativeTimeFormat(undefined, { numeric: "auto", style: "narrow" });
const UNITS: readonly (readonly [Intl.RelativeTimeFormatUnit, number])[] = [
  ["second", 60],
  ["minute", 60],
  ["hour", 24],
  ["day", 7],
  ["week", 4.35],
  ["month", 12],
  ["year", Infinity],
];

export function isPast(iso: string, now: number = Date.now()): boolean {
  return Date.parse(iso) <= now;
}

export function ago(iso: string, now: number = Date.now()): string {
  let amount = (Date.parse(iso) - now) / 1000;
  for (const [unit, size] of UNITS) {
    if (Math.abs(amount) < size) {
      return relative.format(Math.round(amount), unit);
    }
    amount /= size;
  }
  return "";
}
