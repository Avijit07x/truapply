import type { Column } from "../../api/types";
import { Link } from "../../lib/router";
import { ArrowRight, Check } from "../../ui/icons";
import styles from "./Home.module.css";
import { QueueItem } from "./QueueItem";

export function NeedsYou({ columns }: { columns: readonly Column[] }) {
  const ready = columns.find((column) => column.status === "ready");
  const total = ready?.total ?? 0;
  return (
    <section className={styles.needs} aria-labelledby="needs-title">
      <header className={styles.railHead}>
        <h2 id="needs-title" className={styles.railTitle}>
          Ready for you to apply
        </h2>
        <span className={styles.railMeta}>{total.toLocaleString()}</span>
      </header>
      {ready && total > 0 ? (
        <>
          <p className={styles.hint}>
            Open one in your Chrome. The SatyaApply extension fills it in; you check it and press
            Submit.
          </p>
          <ul className={styles.queue}>
            {ready.jobs.map((job) => (
              <QueueItem key={job.id} job={job} />
            ))}
          </ul>
          {total > ready.jobs.length && (
            <Link to="/jobs?status=ready" className={styles.more}>
              See all {total.toLocaleString()}
              <ArrowRight size={12} />
            </Link>
          )}
        </>
      ) : (
        <p className={styles.calm}>
          <Check size={14} />
          Nothing ready yet. New ones show up after a run.
        </p>
      )}
    </section>
  );
}
