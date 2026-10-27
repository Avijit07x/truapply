import type { Column } from "../../api/types";
import { Link } from "../../lib/router";
import { ArrowRight } from "../../ui/icons";
import styles from "./Home.module.css";
import { QueueItem } from "./QueueItem";

const SHOWN = 5;

export function Recent({ columns }: { columns: readonly Column[] }) {
  const applied = columns.find((column) => column.status === "applied");
  if (!applied || applied.total === 0) {
    return null;
  }
  return (
    <section className={styles.recent} aria-labelledby="recent-title">
      <header className={styles.railHead}>
        <h2 id="recent-title" className={styles.railTitle}>
          Recently applied
        </h2>
        <Link to="/jobs?status=applied" className={styles.railLink}>
          See all {applied.total.toLocaleString()}
          <ArrowRight size={12} />
        </Link>
      </header>
      <ul className={styles.queue}>
        {applied.jobs.slice(0, SHOWN).map((job) => (
          <QueueItem key={job.id} job={job} />
        ))}
      </ul>
    </section>
  );
}
