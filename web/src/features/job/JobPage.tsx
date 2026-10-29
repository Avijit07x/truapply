import { useSuspenseQuery } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import { listedOnly } from "../../domain/sources";
import { sitePage } from "../../lib/pages";
import type { PageProps } from "../../lib/router";
import { BackToWhereYouWere } from "../../ui/Blocks";
import { JobView } from "./JobView";

export default function JobPage({ params }: PageProps) {
  const id = Number(params[0]);
  const { data: job } = useSuspenseQuery(queries.job(id));
  return (
    <JobView
      job={job}
      docked
      top={<BackToWhereYouWere fallback={listedOnly(job) ? sitePage(job.source) : "/jobs"} />}
    />
  );
}
