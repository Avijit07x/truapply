import type { JobDetail } from "../../api/types";
import { StatusDot } from "../../components/StatusDot";
import { sourceLabel } from "../../domain/sources";
import { ago, when } from "../../lib/format";
import { ExternalLink } from "../../ui/ExternalLink";
import styles from "./Job.module.css";

export function JobMeta({ job }: { job: JobDetail }) {
  return (
    <p className={styles.meta}>
      <StatusDot status={job.status} />
      <span>{job.score === null ? "Not scored yet" : `Score ${String(job.score)}`}</span>
      <span>{sourceLabel(job.source)}</span>
      <time dateTime={job.updatedAt} title={when(job.updatedAt)}>
        Updated {ago(job.updatedAt)}
      </time>
      {job.url && (
        <span>
          <ExternalLink href={job.url}>Job post</ExternalLink>
        </span>
      )}
      {job.applyUrl && (
        <span>
          <ExternalLink href={job.applyUrl}>Application form</ExternalLink>
        </span>
      )}
    </p>
  );
}
