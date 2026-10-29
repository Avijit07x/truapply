import { Popover } from "@base-ui/react/popover";
import { useState } from "react";
import type { JobQuery } from "../../api/types";
import { type When, dayStart } from "../../domain/dates";
import { jobsHref } from "../../domain/filters";
import { cx } from "../../lib/cx";
import { navigate } from "../../lib/router";
import { Button } from "../../ui/Button";
import { Calendar } from "../../ui/Calendar";
import { ChevronDown, Clock } from "../../ui/icons";
import styles from "./Jobs.module.css";

const PRESETS: readonly { when: Exclude<When, "custom"> | undefined; label: string }[] = [
  { when: undefined, label: "Any time" },
  { when: "today", label: "Today" },
  { when: "week", label: "This week" },
  { when: "month", label: "This month" },
];

const SHORT = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short" });

function rangeLabel({ from, to }: JobQuery): string {
  const start = from ? SHORT.format(dayStart(from)) : "";
  const end = to ? SHORT.format(dayStart(to)) : "";
  if (start && end) return start === end ? start : `${start} – ${end}`;
  return start ? `Since ${start}` : `Until ${end}`;
}

function labelOf(query: JobQuery): string {
  if (query.when === "custom") return rangeLabel(query);
  return PRESETS.find((preset) => preset.when === query.when)?.label ?? "Any time";
}

export function DateFilter({ query }: { query: JobQuery }) {
  const [open, setOpen] = useState(false);
  const [from, setFrom] = useState(query.from ?? "");
  const [to, setTo] = useState(query.to ?? "");
  const base: JobQuery = {
    ...query,
    when: undefined,
    from: undefined,
    to: undefined,
    page: undefined,
  };
  const go = (next: JobQuery) => {
    navigate(jobsHref(next));
    setOpen(false);
  };
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger
        className={styles.menuButton}
        aria-label={`Updated: ${labelOf(query)}`}
        aria-current={query.when ? "true" : undefined}
      >
        <Clock size={14} />
        {labelOf(query)}
        <ChevronDown size={10} />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner className={styles.positioner} sideOffset={6} align="start">
          <Popover.Popup className={cx(styles.popup, styles.datePopup)}>
            <div className={styles.dateSide}>
              <Popover.Title className={styles.popupTitle}>Updated</Popover.Title>
              <div className={styles.statusChoices} role="group" aria-label="Updated">
                {PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    className={styles.choice}
                    aria-pressed={query.when === preset.when}
                    onClick={() => {
                      go({ ...base, when: preset.when });
                    }}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
            <div className={styles.dateMain}>
              <span className={styles.popupTitle}>Custom range</span>
              <Calendar
                from={from}
                to={to}
                onPick={(start, end) => {
                  setFrom(start);
                  setTo(end);
                }}
              />
              <Button
                variant="primary"
                disabled={from === ""}
                onClick={() => {
                  go({ ...base, when: "custom", from: from || undefined, to: to || undefined });
                }}
              >
                Show these dates
              </Button>
            </div>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
