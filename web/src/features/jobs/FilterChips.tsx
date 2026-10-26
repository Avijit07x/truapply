import type { JobFilter, Status } from "../../api/types";
import { GROUP_LABEL } from "../../domain/groups";
import { STATUS, STATUSES } from "../../domain/status";
import { Link } from "../../lib/router";
import { Close } from "../../ui/icons";
import styles from "./Jobs.module.css";

type Chip = { to: string; label: string; count: number; on: boolean };

type FilterChipsProps = {
  filter: JobFilter;
  counts: Partial<Record<Status, number>>;
  total: number;
};

function chips({ filter, counts, total }: FilterChipsProps): Chip[] {
  const all = { to: "/jobs", label: "All", count: total, on: !filter.status && !filter.group };
  const statuses = STATUSES.filter(
    (status) => (counts[status] ?? 0) > 0 || status === filter.status,
  ).map((status) => ({
    to: `/jobs?status=${status}`,
    label: STATUS[status].label,
    count: counts[status] ?? 0,
    on: status === filter.status,
  }));
  return [all, ...statuses];
}

export function FilterChips(props: FilterChipsProps) {
  const { group } = props.filter;
  return (
    <nav className={styles.chips} aria-label="Filter by status">
      {group && (
        <Link to="/jobs" className={styles.chip} aria-current="true">
          From the workflow map: {GROUP_LABEL[group]}
          <Close size={10} />
        </Link>
      )}
      {chips(props).map((chip) => (
        <Link
          key={chip.to}
          to={chip.to}
          className={styles.chip}
          aria-current={chip.on ? "true" : undefined}
        >
          {chip.label}
          <span className={styles.chipCount}>{chip.count.toLocaleString()}</span>
        </Link>
      ))}
    </nav>
  );
}
