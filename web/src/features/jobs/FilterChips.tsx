import type { JobQuery, Status } from "../../api/types";
import { jobsHref } from "../../domain/filters";
import { GROUP_LABEL } from "../../domain/groups";
import { STATUS, STATUSES } from "../../domain/status";
import { Link } from "../../lib/router";
import { Close } from "../../ui/icons";
import styles from "./Jobs.module.css";

type Chip = { to: string; label: string; count: number; on: boolean };

type FilterChipsProps = {
  query: JobQuery;
  counts: Partial<Record<Status, number>>;
  total: number;
};

function chips({ query, counts, total }: FilterChipsProps): Chip[] {
  const kept: JobQuery = { q: query.q, sort: query.sort, order: query.order };
  const all = {
    to: jobsHref({ ...kept, show: "all" }),
    label: "All",
    count: total,
    on: query.show === "all" && !query.status && !query.group,
  };
  const active = {
    to: jobsHref(kept),
    label: "Active",
    count: total - (counts.skipped ?? 0),
    on: !query.show && !query.status && !query.group,
  };
  const statuses = STATUSES.filter(
    (status) => (counts[status] ?? 0) > 0 || status === query.status,
  ).map((status) => ({
    to: jobsHref({ ...kept, status }),
    label: STATUS[status].label,
    count: counts[status] ?? 0,
    on: status === query.status,
  }));
  return [all, active, ...statuses];
}

export function FilterChips(props: FilterChipsProps) {
  const { group, q, sort, order } = props.query;
  return (
    <nav className={styles.chips} aria-label="Filter by status">
      {group && (
        <Link to={jobsHref({ q, sort, order })} className={styles.chip} aria-current="true">
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
