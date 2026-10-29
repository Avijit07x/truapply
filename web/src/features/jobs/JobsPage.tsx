import { PAGE_NAMES } from "../../lib/pages";
import { cx } from "../../lib/cx";
import type { PageProps } from "../../lib/router";
import { PageHeader } from "../../ui/Blocks";
import { ActiveFilters } from "./ActiveFilters";
import { FilterChips } from "./FilterChips";
import styles from "./Jobs.module.css";
import { JobsFilter } from "./JobsFilter";
import { JobSplit } from "./JobSplit";
import { JobsSearch, describe, titleOf, useJobs } from "./useJobs";

export default function JobsPage({ params }: PageProps) {
  const { query, summary, list, counts, total } = useJobs(params, false);
  const filters = { query, counts, total };
  return (
    <div className={cx(styles.page, styles.edge)}>
      <PageHeader title={titleOf(query, PAGE_NAMES["/jobs"])} description={describe(query, list)} />
      <JobSplit
        query={query}
        list={list}
        tools={
          <>
            <div className={styles.findRow}>
              <JobsSearch query={query} />
              <JobsFilter summary={summary} {...filters} />
            </div>
            <FilterChips {...filters} withAll={false} />
            <ActiveFilters query={query} />
          </>
        }
      />
    </div>
  );
}
