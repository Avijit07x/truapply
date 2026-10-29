import type { JobQuery, Status } from "../../api/types";
import { jobsHref } from "../../domain/filters";
import { GROUP_LABEL } from "../../domain/groups";
import { STATUS, STATUSES, activeCount } from "../../domain/status";
import { Link } from "../../lib/router";
import { Close } from "../../ui/icons";
import { ChipMenu, type MenuChoice } from "./ChipMenu";
import styles from "./Jobs.module.css";

type Chip = { to: string; label: string; count: number; on: boolean };

type FilterChipsProps = {
  query: JobQuery;
  counts: Partial<Record<Status, number>>;
  total: number;
};

function kept(query: JobQuery): JobQuery {
  return { q: query.q, sort: query.sort, order: query.order, source: query.source };
}

function chips({ query, counts, total }: FilterChipsProps): Chip[] {
  const all = {
    to: jobsHref({ ...kept(query), show: "all" }),
    label: "All",
    count: total,
    on: query.show === "all" && !query.status && !query.group,
  };
  const active = {
    to: jobsHref(kept(query)),
    label: "Active",
    count: activeCount(counts, total),
    on: !query.show && !query.status && !query.group,
  };
  return [all, active];
}

function statusChoices({ query, counts }: FilterChipsProps): MenuChoice[] {
  return STATUSES.filter((status) => (counts[status] ?? 0) > 0 || status === query.status).map(
    (status) => ({
      key: status,
      to: jobsHref({ ...kept(query), status }),
      label: STATUS[status].label,
      count: counts[status] ?? 0,
    }),
  );
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
      <ChipMenu
        label="Status"
        title="Status"
        choices={statusChoices(props)}
        picked={props.query.status ?? null}
        anyTo={jobsHref(kept(props.query))}
      />
    </nav>
  );
}
