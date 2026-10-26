import type { ReactNode } from "react";
import type { JobRow } from "../api/types";
import { when } from "../lib/format";
import { Link } from "../lib/router";
import { Empty, List } from "../ui/Blocks";
import styles from "./JobList.module.css";
import { StatusPill } from "./StatusPill";

export function place(job: JobRow): string {
  return [job.company, job.location].filter(Boolean).join(" · ");
}

export function Score({ value }: { value: number | null }) {
  return value === null ? null : (
    <span className={styles.score} title="Match score">
      {value}
    </span>
  );
}

type JobListProps = { jobs: readonly JobRow[]; empty: ReactNode; showStatus?: boolean };

export function JobList({ jobs, empty, showStatus = true }: JobListProps) {
  if (jobs.length === 0) {
    return <Empty>{empty}</Empty>;
  }
  return (
    <List>
      {jobs.map((job) => (
        <li key={job.id}>
          <Link to={`/jobs/${String(job.id)}`} className={styles.row}>
            <span className={styles.main}>
              <strong className={styles.title}>{job.title}</strong>
              <span className={styles.place}>{place(job)}</span>
            </span>
            <span className={styles.meta}>
              <Score value={job.score} />
              {showStatus && <StatusPill status={job.status} />}
              <time dateTime={job.updatedAt}>{when(job.updatedAt)}</time>
            </span>
          </Link>
        </li>
      ))}
    </List>
  );
}
