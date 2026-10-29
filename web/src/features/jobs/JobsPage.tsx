import { useSuspenseQueries } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import type { JobList, JobQuery } from "../../api/types";
import { jobQuery, jobsHref } from "../../domain/filters";
import { GROUP_LABEL } from "../../domain/groups";
import { STATUS } from "../../domain/status";
import { plural } from "../../lib/format";
import { PAGE_NAMES } from "../../lib/pages";
import { type PageProps, navigate, useLocation } from "../../lib/router";
import { isSource, sourceLabel } from "../../domain/sources";
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
  const where = query.source ? `${sourceLabel(query.source)} jobs` : PAGE_NAMES["/jobs"];
  return query.status ? `${where}: ${STATUS[query.status].label}` : where;
}

function describe(query: JobQuery, list: JobList): string {
  const count = plural(list.total, "job");
  if (query.q) {
    return `${count} matching “${query.q}”`;
  }
  const narrowed =
    query.show ?? query.status ?? query.group ?? query.company ?? query.location ?? query.minScore;
  return narrowed === undefined ? `${count}, not counting skipped or closed ones` : count;
}

export default function JobsPage({ params }: PageProps) {
  const { url, pending } = useLocation();
  const site = params[0] ?? null;
  const query = { ...jobQuery(url.searchParams), source: isSource(site) ? site : undefined };
  const [{ data: summary }, { data: list }] = useSuspenseQueries({
    queries: [queries.summary(), queries.jobs(query)],
  });
  const listed = summary.sites.find((item) => item.source === query.source);
  const counts = listed?.counts ?? summary.counts;
  const total = listed?.total ?? summary.total;
  return (
    <div className={styles.page}>
      <PageHeader
        title={titleOf(query)}
        description={describe(query, list)}
        actions={!query.source && <AddLink />}
      />
      <div className={styles.toolbar}>
        <FilterChips query={query} counts={counts} total={total} />
        <SearchBox
          value={query.q ?? ""}
          onSearch={(q) => {
            navigate(jobsHref({ ...query, q: q === "" ? undefined : q, page: undefined }), true);
          }}
        />
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
  );
}
