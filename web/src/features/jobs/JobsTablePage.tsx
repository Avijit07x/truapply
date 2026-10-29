import { PAGE_NAMES } from "../../lib/pages";
import { cx } from "../../lib/cx";
import type { PageProps } from "../../lib/router";
import { PageHeader } from "../../ui/Blocks";
import { ActiveFilters } from "./ActiveFilters";
import { AddLink } from "./AddLink";
import { JobGrid } from "./JobGrid";
import styles from "./Jobs.module.css";
import { Pager } from "./Pager";
import { DateFilter } from "./DateFilter";
import { JobsFilter } from "./JobsFilter";
import { JobsSearch, describe, titleOf, useJobs } from "./useJobs";

export default function JobsTablePage({ params }: PageProps) {
  const { query, summary, list, pending, counts, total } = useJobs(params, true);
  const filters = { query, counts, total };
  return (
    <div className={cx(styles.page, styles.edge)}>
      <PageHeader
        title={titleOf(query, PAGE_NAMES["/jobs/table"])}
        description={describe(query, list)}
      />
      <div className={styles.tableView}>
        <div className={styles.tools}>
          <JobsSearch query={query} />
          <JobsFilter summary={summary} {...filters} />
          <DateFilter query={query} />
          {!query.source && (
            <div className={styles.toolsEnd}>
              <AddLink />
            </div>
          )}
        </div>
        <ActiveFilters query={query} />
        <JobGrid query={query} list={list} counts={counts} total={total} pending={pending} />
        <footer className={styles.footer}>
          <p className={styles.keys}>
            <kbd>↑</kbd>
            <kbd>↓</kbd> move <kbd>Enter</kbd> open <kbd>X</kbd> select
          </p>
          <Pager query={query} list={list} />
        </footer>
      </div>
    </div>
  );
}
