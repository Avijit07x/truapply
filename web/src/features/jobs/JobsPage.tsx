import { useSuspenseQueries } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import type { JobFilter } from "../../api/types";
import { JobList } from "../../components/JobList";
import { jobFilter } from "../../domain/filters";
import { GROUP_LABEL } from "../../domain/groups";
import { STATUS } from "../../domain/status";
import { plural } from "../../lib/format";
import { useLocation } from "../../lib/router";
import { PageHeader, Stack } from "../../ui/Blocks";
import { FilterChips } from "./FilterChips";

function titleOf(filter: JobFilter): string {
  if (filter.group) {
    return GROUP_LABEL[filter.group];
  }
  return filter.status ? STATUS[filter.status].label : "All jobs";
}

export default function JobsPage() {
  const { url } = useLocation();
  const filter = jobFilter(url.searchParams);
  const [{ data: summary }, { data: list }] = useSuspenseQueries({
    queries: [queries.summary(), queries.jobs(filter)],
  });
  const shown = list.jobs.length;
  const description =
    list.total > shown
      ? `Showing the newest ${shown.toLocaleString()} of ${list.total.toLocaleString()}.`
      : plural(list.total, "job");
  return (
    <>
      <PageHeader title={titleOf(filter)} description={description} />
      <Stack>
        <FilterChips filter={filter} counts={summary.counts} total={summary.total} />
        <JobList jobs={list.jobs} empty="No jobs here yet." />
      </Stack>
    </>
  );
}
