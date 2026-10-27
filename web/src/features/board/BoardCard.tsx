import type { JobRow } from "../../api/types";
import { Score } from "../../components/JobList";
import { cx } from "../../lib/cx";
import { ago, when } from "../../lib/format";
import { Link } from "../../lib/router";
import styles from "./Board.module.css";
import { canMove, useDrag } from "./dragStore";

const TINTS = ["accent", "good", "warn", "auto", "bad", "plain"] as const;

function tint(name: string): (typeof TINTS)[number] {
  let hash = 0;
  for (const letter of name) {
    hash = (hash * 31 + (letter.codePointAt(0) ?? 0)) % 997;
  }
  return TINTS[hash % TINTS.length] ?? "plain";
}

function initial(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "?";
}

export function BoardCard({ job }: { job: JobRow }) {
  const startDrag = useDrag((state) => state.startDrag);
  const endDrag = useDrag((state) => state.endDrag);
  const dragging = useDrag((state) => state.dragging?.id === job.id);
  const movable = canMove(job);
  return (
    <Link
      to={`/jobs/${String(job.id)}`}
      className={cx(styles.card, movable && styles.movable, dragging && styles.dragging)}
      draggable={movable}
      title={movable ? "Drag to Applied once you submitted it, or to Dismiss" : undefined}
      onDragStart={(event) => {
        event.dataTransfer.setData("text/plain", String(job.id));
        event.dataTransfer.effectAllowed = "move";
        startDrag(job);
      }}
      onDragEnd={endDrag}
    >
      <span className={styles.cardTop}>
        <span className={cx(styles.avatar, styles[tint(job.company)])} aria-hidden="true">
          {initial(job.company)}
        </span>
        <span className={styles.cardText}>
          <strong className={styles.cardTitle}>{job.title}</strong>
          <span className={styles.place}>
            {[job.company, job.location].filter(Boolean).join(" · ")}
          </span>
        </span>
      </span>
      <span className={styles.meta}>
        <Score value={job.score} />
        <time dateTime={job.updatedAt} title={when(job.updatedAt)}>
          {ago(job.updatedAt)}
        </time>
      </span>
    </Link>
  );
}
