import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { dayOf, dayStart } from "../domain/dates";
import { cx } from "../lib/cx";
import { IconButton } from "./Button";
import styles from "./Calendar.module.css";
import { ChevronLeft, ChevronRight } from "./icons";

type CalendarProps = { from: string; to: string; onPick: (from: string, to: string) => void };

const MONTH = new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" });
const LONG = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "long", year: "numeric" });
const WEEKDAY = new Intl.DateTimeFormat(undefined, { weekday: "narrow" });
const WEEKDAYS = Array.from({ length: 7 }, (_, index) =>
  WEEKDAY.format(new Date(2024, 0, 1 + index)),
);

const MOVES: Partial<Record<string, number>> = {
  ArrowLeft: -1,
  ArrowRight: 1,
  ArrowUp: -7,
  ArrowDown: 7,
};

function monthOf(day: string): Date {
  const date = dayStart(day);
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function shifted(day: string, days: number): string {
  const date = dayStart(day);
  date.setDate(date.getDate() + days);
  return dayOf(date);
}

function daysOf(month: Date): string[] {
  const count = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
  return Array.from({ length: count }, (_, index) =>
    dayOf(new Date(month.getFullYear(), month.getMonth(), index + 1)),
  );
}

function picked(day: string, from: string, to: string): [string, string] {
  return from === "" || to !== "" || day < from ? [day, ""] : [from, day];
}

export function Calendar({ from, to, onPick }: CalendarProps) {
  const today = dayOf(new Date());
  const [focus, setFocus] = useState(to || from || today);
  const [moved, setMoved] = useState(false);
  const grid = useRef<HTMLDivElement>(null);
  const month = monthOf(focus);
  const days = daysOf(month);
  const lead = (month.getDay() + 6) % 7;
  const lastShown = days.at(-1) ?? today;

  useEffect(() => {
    if (moved) grid.current?.querySelector<HTMLElement>('[tabindex="0"]')?.focus();
  }, [focus, moved]);

  const turn = (months: number) => {
    const first = new Date(month.getFullYear(), month.getMonth() + months, 1);
    const day = dayOf(first);
    setFocus(day > today ? today : day);
    setMoved(false);
  };

  const onKeyDown = (event: KeyboardEvent) => {
    const move = MOVES[event.key];
    if (move === undefined) return;
    event.preventDefault();
    const next = shifted(focus, move);
    if (next <= today) {
      setFocus(next);
      setMoved(true);
    }
  };

  return (
    <div className={styles.calendar}>
      <div className={styles.head}>
        <strong aria-live="polite">{MONTH.format(month)}</strong>
        <IconButton
          label="Previous month"
          onClick={() => {
            turn(-1);
          }}
        >
          <ChevronLeft size={14} />
        </IconButton>
        <IconButton
          label="Next month"
          disabled={lastShown >= today}
          onClick={() => {
            turn(1);
          }}
        >
          <ChevronRight size={14} />
        </IconButton>
      </div>
      <div ref={grid} className={styles.grid} role="group" aria-label="Dates" onKeyDown={onKeyDown}>
        {WEEKDAYS.map((weekday, index) => (
          <span key={index} className={styles.weekday} aria-hidden="true">
            {weekday}
          </span>
        ))}
        {lead > 0 && <span style={{ gridColumn: `span ${String(lead)}` }} />}
        {days.map((day) => (
          <button
            key={day}
            type="button"
            className={cx(
              styles.day,
              from !== "" && to !== "" && day > from && day < to && styles.between,
            )}
            tabIndex={day === focus ? 0 : -1}
            disabled={day > today}
            aria-label={LONG.format(dayStart(day))}
            aria-pressed={day === from || day === to}
            aria-current={day === today ? "date" : undefined}
            onClick={() => {
              setFocus(day);
              onPick(...picked(day, from, to));
            }}
          >
            {dayStart(day).getDate()}
          </button>
        ))}
      </div>
    </div>
  );
}
