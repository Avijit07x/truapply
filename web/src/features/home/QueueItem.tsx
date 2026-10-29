import type { JobRow } from "../../api/types";
import { Score } from "../../components/JobList";
import { sourceLabel } from "../../domain/sources";
import { when } from "../../lib/format";
import { Link } from "../../lib/router";
import { Ago } from "../../ui/Ago";
import { ArrowRight } from "../../ui/icons";
import styles from "./Home.module.css";

export function QueueItem({ job }: { job: JobRow }) {
  const where = [job.company, job.location, sourceLabel(job.source)].filter(Boolean).join(" · ");
  return (
    <li>
      <Link to={`/jobs/${String(job.id)}`} className={styles.item}>
        <span className={styles.mono} aria-hidden="true">
          {job.company.slice(0, 1).toUpperCase()}
        </span>
        <span className={styles.itemText}>
          <strong className={styles.itemTitle}>{job.title}</strong>
          <span className={styles.itemPlace}>{where}</span>
        </span>
        <Score value={job.score} />
        <time className={styles.itemWhen} dateTime={job.updatedAt} title={when(job.updatedAt)}>
          <Ago iso={job.updatedAt} />
        </time>
        <ArrowRight size={12} className={styles.itemArrow} />
      </Link>
    </li>
  );
}
