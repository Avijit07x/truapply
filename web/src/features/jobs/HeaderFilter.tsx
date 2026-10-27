import { Popover } from "@base-ui/react/popover";
import { useState } from "react";
import type { JobQuery, Summary } from "../../api/types";
import { jobsHref } from "../../domain/filters";
import { STATUS, STATUSES } from "../../domain/status";
import { cx } from "../../lib/cx";
import { navigate } from "../../lib/router";
import { Filter } from "../../ui/icons";
import { SearchBox } from "../../ui/SearchBox";
import styles from "./Jobs.module.css";

export type FilterKind = "company" | "location" | "minScore" | "status";

const LOWEST_SCORES = [60, 70, 80, 90] as const;
const TITLE: Record<FilterKind, string> = {
  company: "Company contains",
  location: "Location contains",
  minScore: "Score at least",
  status: "Status",
};

type ChoiceProps = {
  query: JobQuery;
  counts: Summary["counts"];
  total: number;
  go: (next: JobQuery, replace?: boolean) => void;
};

function isOn(kind: FilterKind, query: JobQuery): boolean {
  return query[kind] !== undefined;
}

function Choice({
  on,
  label,
  count,
  onPick,
}: {
  on: boolean;
  label: string;
  count?: number;
  onPick: () => void;
}) {
  return (
    <button type="button" className={styles.choice} aria-pressed={on} onClick={onPick}>
      {label}
      {count !== undefined && <span className={styles.choiceCount}>{count.toLocaleString()}</span>}
    </button>
  );
}

function ScoreChoices({ query, go }: ChoiceProps) {
  return (
    <div className={styles.scoreChoices} role="group" aria-label={TITLE.minScore}>
      <Choice
        on={query.minScore === undefined}
        label="Any"
        onPick={() => {
          go({ ...query, minScore: undefined });
        }}
      />
      {LOWEST_SCORES.map((score) => (
        <Choice
          key={score}
          on={query.minScore === score}
          label={`${String(score)}+`}
          onPick={() => {
            go({ ...query, minScore: score });
          }}
        />
      ))}
    </div>
  );
}

function StatusChoices({ query, counts, total, go }: ChoiceProps) {
  const pick = (status: JobQuery["status"], show?: "all") => () => {
    go({ ...query, group: undefined, status, show });
  };
  return (
    <div className={styles.statusChoices} role="group" aria-label={TITLE.status}>
      <Choice
        on={query.show === "all" && !query.status && !query.group}
        label="All"
        count={total}
        onPick={pick(undefined, "all")}
      />
      <Choice
        on={!query.show && !query.status && !query.group}
        label="Active"
        count={total - (counts.skipped ?? 0)}
        onPick={pick(undefined)}
      />
      {STATUSES.filter((status) => (counts[status] ?? 0) > 0).map((status) => (
        <Choice
          key={status}
          on={query.status === status}
          label={STATUS[status].label}
          count={counts[status] ?? 0}
          onPick={pick(status)}
        />
      ))}
    </div>
  );
}

function Body({ kind, ...props }: ChoiceProps & { kind: FilterKind }) {
  const { query, go } = props;
  if (kind === "minScore") {
    return <ScoreChoices {...props} />;
  }
  if (kind === "status") {
    return <StatusChoices {...props} />;
  }
  return (
    <SearchBox
      label={TITLE[kind]}
      placeholder="Type a few letters"
      autoFocus
      wide
      value={query[kind] ?? ""}
      onSearch={(value) => {
        const text = value === "" ? undefined : value;
        go(kind === "company" ? { ...query, company: text } : { ...query, location: text }, true);
      }}
    />
  );
}

type HeaderFilterProps = Omit<ChoiceProps, "go"> & { kind: FilterKind; label: string };

export function HeaderFilter({ kind, label, ...props }: HeaderFilterProps) {
  const [open, setOpen] = useState(false);
  const go = (next: JobQuery, replace = false) => {
    navigate(jobsHref({ ...next, page: undefined }), replace);
    if (kind === "status") {
      setOpen(false);
    }
  };
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger
        className={cx(styles.filterButton, isOn(kind, props.query) && styles.filterOn)}
        aria-label={`Filter by ${label.toLowerCase()}`}
      >
        <Filter size={12} />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner className={styles.positioner} sideOffset={6} align="start">
          <Popover.Popup className={styles.popup}>
            <Popover.Title className={styles.popupTitle}>{TITLE[kind]}</Popover.Title>
            <Body kind={kind} go={go} {...props} />
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
