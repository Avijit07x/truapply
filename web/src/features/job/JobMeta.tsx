import type { ReactNode } from "react";
import type { JobDetail, Status } from "../../api/types";
import { StatusDot } from "../../components/StatusDot";
import { sourceLabel } from "../../domain/sources";
import { when } from "../../lib/format";
import { Ago } from "../../ui/Ago";
import { ExternalLink } from "../../ui/ExternalLink";
import styles from "./Job.module.css";

const OPENS_FORM = new Set<Status>(["ready", "scored"]);

export function JobMeta({ job, children }: { job: JobDetail; children?: ReactNode }) {
  return (
    <p className={styles.meta}>
      <StatusDot status={job.status} auto={job.autoSubmitted} />
      <span>{sourceLabel(job.source)}</span>
      <time dateTime={job.updatedAt} title={when(job.updatedAt)}>
        Updated <Ago iso={job.updatedAt} />
      </time>
      {job.url && (
        <span>
          <ExternalLink href={job.url}>Job post</ExternalLink>
        </span>
      )}
      {job.applyUrl && !OPENS_FORM.has(job.status) && (
        <span>
          <ExternalLink href={job.applyUrl}>Application form</ExternalLink>
        </span>
      )}
      {children}
    </p>
  );
}
