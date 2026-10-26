import type { JobRow } from "../../api/types";
import { Score, place } from "../../components/JobList";
import { cx } from "../../lib/cx";
import { when } from "../../lib/format";
import { Link } from "../../lib/router";
import styles from "./Board.module.css";
import { canMove, useDrag } from "./dragStore";

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
      title={movable ? "Drag to Approved, or to Dismiss" : undefined}
      onDragStart={(event) => {
        event.dataTransfer.setData("text/plain", String(job.id));
        event.dataTransfer.effectAllowed = "move";
        startDrag(job);
      }}
      onDragEnd={endDrag}
    >
      <strong className={styles.cardTitle}>{job.title}</strong>
      <span className={styles.place}>{place(job)}</span>
      <span className={styles.meta}>
        <Score value={job.score} />
        <time dateTime={job.updatedAt}>{when(job.updatedAt)}</time>
      </span>
    </Link>
  );
}
