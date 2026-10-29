import { useSuspenseQueries } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import type { JobList, JobQuery, Status } from "../../api/types";
import { jobQuery, jobsHref, listQuery } from "../../domain/filters";
import { GROUP_LABEL } from "../../domain/groups";
import { isSource, sourceLabel } from "../../domain/sources";
import { STATUS } from "../../domain/status";
import { plural } from "../../lib/format";
import { useLocation } from "../../lib/router";
import { navigate } from "../../lib/router";
import { SearchBox } from "../../ui/SearchBox";

const CAREER_JOBS = "Career jobs";

function added(all: readonly Partial<Record<Status, number>>[]): Partial<Record<Status, number>> {
  const sum: Partial<Record<Status, number>> = {};
  for (const counts of all) {
    for (const [status, count] of Object.entries(counts) as [Status, number][]) {
      sum[status] = (sum[status] ?? 0) + count;
    }
  }
  return sum;
}

export function titleOf(query: JobQuery, page: string): string {
  if (query.group) {
    return GROUP_LABEL[query.group];
  }
  const site = query.sites === "career" ? CAREER_JOBS : page;
  const where = query.source ? `${sourceLabel(query.source)} jobs` : site;
  return query.status ? `${where}: ${STATUS[query.status].label}` : where;
}

export function describe(query: JobQuery, list: JobList): string {
  const count = plural(list.total, "job");
  if (query.q) {
    return `${count} matching “${query.q}”`;
  }
  const narrowed =
    query.show ??
    query.status ??
    query.group ??
    query.company ??
    query.location ??
    query.minScore ??
    query.when;
  return narrowed === undefined ? `${count}, not counting skipped or closed ones` : count;
}

export function useJobs(params: readonly string[], table: boolean) {
  const { url, pending } = useLocation();
  const site = params[0] ?? null;
  const asked = { ...jobQuery(url.searchParams), source: isSource(site) ? site : undefined };
  const fetched = table
    ? { ...asked, sites: asked.sites === "all" ? ("all" as const) : undefined }
    : listQuery(asked);
  const [{ data: summary }, { data: list }] = useSuspenseQueries({
    queries: [queries.summary(), queries.jobs(fetched)],
  });
  const listed = summary.sites.find((item) => item.source === asked.source);
  const query: JobQuery = table ? { ...asked, table: true } : asked;
  const everywhere = fetched.sites === "all";
  return {
    query,
    summary,
    list,
    pending,
    counts: everywhere
      ? added([summary.counts, ...summary.sites.map((item) => item.counts)])
      : (listed?.counts ?? summary.counts),
    total: everywhere
      ? summary.sites.reduce((sum, item) => sum + item.total, summary.total)
      : (listed?.total ?? summary.total),
  };
}

export function JobsSearch({ query }: { query: JobQuery }) {
  return (
    <SearchBox
      value={query.q ?? ""}
      onSearch={(q) => {
        navigate(jobsHref({ ...query, q: q === "" ? undefined : q, page: undefined }), true);
      }}
    />
  );
}
