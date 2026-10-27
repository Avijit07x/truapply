import type { JobDetail } from "../../api/types";
import { Callout } from "../../ui/Callout";

export function NextStep({ job }: { job: JobDetail }) {
  if (job.status === "ready") {
    return (
      <Callout>
        Open it in your Chrome. The SatyaApply extension fills it in; you check it and press Submit.
      </Callout>
    );
  }
  if (job.status === "scored") {
    return <Callout>A good match, not tailored yet. You can open it in your Chrome now.</Callout>;
  }
  return null;
}
