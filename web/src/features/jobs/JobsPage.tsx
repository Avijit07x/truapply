import { useSuspenseQueries } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import type { JobList, JobQuery } from "../../api/types";
import { jobQuery, jobsHref } from "../../domain/filters";
import { GROUP_LABEL } from "../../domain/groups";
import { STATUS } from "../../domain/status";
import { plural } from "../../lib/format";
import { navigate, useLocation } from "../../lib/router";
import { PageHeader } from "../../ui/Blocks";
import { FilterChips } from "./FilterChips";
import { SearchBox } from "../../ui/SearchBox";
import styles from "./Jobs.module.css";
import { ActiveFilters } from "./ActiveFilters";
import { AddLink } from "./AddLink";
import { JobGrid } from "./JobGrid";
import { Pager } from "./Pager";

function titleOf(query: JobQuery): string {
  if (query.group) {
    return GROUP_LABEL[query.group];
  }
  return query.status ? STATUS[query.status].label : "All jobs";
}

function describe(query: JobQuery, list: JobList): string {
  const count = plural(list.total, "job");
  if (query.q) {
    return `${count} matching “${query.q}”`;
  }
  const narrowed =
    query.show ?? query.status ?? query.group ?? query.company ?? query.location ?? query.minScore;
  return narrowed === undefined ? `${count}, not counting skipped ones` : count;
}

export default function JobsPage() {
  const { url, pending } = useLocation();
  const query = jobQuery(url.searchParams);
  const [{ data: summary }, { data: list }] = useSuspenseQueries({
    queries: [queries.summary(), queries.jobs(query)],
  });
  return (
    <div className={styles.page}>
      <PageHeader
        title={titleOf(query)}
        description={describe(query, list)}
        actions={
          <>
            <AddLink />
            <SearchBox
              value={query.q ?? ""}
              onSearch={(q) => {
                navigate(
                  jobsHref({ ...query, q: q === "" ? undefined : q, page: undefined }),
                  true,
                );
              }}
            />
          </>
        }
      />
      <FilterChips query={query} counts={summary.counts} total={summary.total} />
      <ActiveFilters query={query} />
      <JobGrid
        query={query}
        list={list}
        counts={summary.counts}
        total={summary.total}
        pending={pending}
      />
      <footer className={styles.footer}>
        <p className={styles.keys}>
          <kbd>↑</kbd>
          <kbd>↓</kbd> move <kbd>Enter</kbd> open <kbd>X</kbd> select
        </p>
        <Pager query={query} list={list} />
      </footer>
    </div>
  );
}
