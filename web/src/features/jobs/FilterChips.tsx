import type { JobQuery, Status } from "../../api/types";
import { jobsHref } from "../../domain/filters";
import { GROUP_LABEL } from "../../domain/groups";
import { STATUS, STATUSES, activeCount } from "../../domain/status";
import { Link } from "../../lib/router";
import { Close } from "../../ui/icons";
import type { MenuChoice } from "./ChipMenu";
import styles from "./Jobs.module.css";

type Chip = { to: string; label: string; count: number; on: boolean };

export type FilterChipsProps = {
  query: JobQuery;
  counts: Partial<Record<Status, number>>;
  total: number;
  withAll?: boolean;
};

const IN_BAR: readonly Status[] = ["ready", "scored", "applied"];

const BAR_LABEL: Partial<Record<Status, string>> = {
  ready: "Ready",
  scored: "Matches",
  applied: "Applied",
};

export function kept(query: JobQuery): JobQuery {
  return {
    q: query.q,
    sort: query.sort,
    order: query.order,
    source: query.source,
    sites: query.sites,
    when: query.when,
    from: query.from,
    to: query.to,
    table: query.table,
  };
}

export function barChoices({ query, counts, total, withAll = true }: FilterChipsProps): Chip[] {
  const plain = !query.status && !query.group;
  const active = {
    to: jobsHref(kept(query)),
    label: "Active",
    count: activeCount(counts, total),
    on: !query.show && plain,
  };
  const statuses = IN_BAR.map((status) => ({
    to: jobsHref({ ...kept(query), status }),
    label: BAR_LABEL[status] ?? STATUS[status].label,
    count: counts[status] ?? 0,
    on: query.status === status,
  }));
  const all = {
    to: jobsHref({ ...kept(query), show: "all" }),
    label: "All",
    count: total,
    on: query.show === "all" && plain,
  };
  return withAll ? [active, ...statuses, all] : [active, ...statuses];
}

export function statusChoices({ query, counts }: FilterChipsProps): MenuChoice[] {
  return STATUSES.filter(
    (status) => !IN_BAR.includes(status) && ((counts[status] ?? 0) > 0 || status === query.status),
  ).map((status) => ({
    key: status,
    to: jobsHref({ ...kept(query), status }),
    label: STATUS[status].label,
    count: counts[status] ?? 0,
  }));
}

export function FilterChips(props: FilterChipsProps) {
  const { group, q, sort, order, table } = props.query;
  return (
    <nav className={styles.chips} aria-label="Filter by status">
      {group && (
        <Link to={jobsHref({ q, sort, order, table })} className={styles.chip} aria-current="true">
          From Today: {GROUP_LABEL[group]}
          <Close size={10} />
        </Link>
      )}
      <div className={styles.segbar}>
        {barChoices(props).map((chip) => (
          <Link
            key={chip.label}
            to={chip.to}
            className={styles.seg}
            aria-current={chip.on ? "true" : undefined}
          >
            {chip.label}
            <span className={styles.segCount}>{chip.count.toLocaleString()}</span>
          </Link>
        ))}
      </div>
    </nav>
  );
}
