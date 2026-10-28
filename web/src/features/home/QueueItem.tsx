import type { JobRow } from "../../api/types";
import { Score, place } from "../../components/JobList";
import { when } from "../../lib/format";
import { Ago } from "../../ui/Ago";
import { Link } from "../../lib/router";
import { ArrowRight } from "../../ui/icons";
import styles from "./Home.module.css";

export function QueueItem({ job }: { job: JobRow }) {
  return (
    <li>
      <Link to={`/jobs/${String(job.id)}`} className={styles.item}>
        <span className={styles.itemText}>
          <strong className={styles.itemTitle}>{job.title}</strong>
          <span className={styles.itemPlace}>{place(job)}</span>
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
