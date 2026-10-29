import type { JobDetail } from "../../api/types";
import { listedOnly, sourceLabel } from "../../domain/sources";
import { Callout } from "../../ui/Callout";

export function NextStep({ job }: { job: JobDetail }) {
  if (job.status === "ready" && listedOnly(job)) {
    return (
      <Callout>
        Apply on {sourceLabel(job.source)} with your own resume, then press I submitted it here.
      </Callout>
    );
  }
  if (job.status === "ready") {
    return (
      <Callout>
        Open it in your Chrome. The TruApply extension fills it in; you check it and press Submit.
      </Callout>
    );
  }
  return null;
}
