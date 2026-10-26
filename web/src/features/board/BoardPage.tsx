import { useSuspenseQuery } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import type { Column, Status } from "../../api/types";
import { DismissForm } from "../../components/DismissForm";
import { STATUS } from "../../domain/status";
import { cx } from "../../lib/cx";
import { Link } from "../../lib/router";
import { PageHeader } from "../../ui/Blocks";
import { Dialog } from "../../ui/Dialog";
import styles from "./Board.module.css";
import { BoardCard } from "./BoardCard";
import { DropZone } from "./DropZone";
import { canMove, useDrag } from "./dragStore";
import { type Move, useMoveCard } from "./useMoveCard";

const COLUMN_NAME: Partial<Record<Status, string>> = {
  needs_input: "Needs your answer",
  finish: "Finish these",
  ready: "Waiting for your OK",
  approved: "Approved",
  applied: "Applied",
  scored: "Good matches to fill",
};

function BoardColumn({ column, onMove }: { column: Column; onMove: (move: Move) => void }) {
  const { label, tone } = STATUS[column.status];
  const name = COLUMN_NAME[column.status] ?? label;
  return (
    <DropZone
      className={styles.column}
      label={name}
      active={column.status === "approved"}
      onDrop={(job) => {
        onMove({ job, to: "approved" });
      }}
    >
      <header className={styles.columnHead}>
        <span className={cx(styles.dot, styles[tone])} aria-hidden="true" />
        <h2 className={styles.columnName}>{name}</h2>
        <span className={styles.count}>{column.total.toLocaleString()}</span>
      </header>
      <div className={styles.cards}>
        {column.jobs.map((job) => (
          <BoardCard key={job.id} job={job} />
        ))}
        {column.jobs.length === 0 && <p className={styles.nothing}>Nothing here</p>}
      </div>
      {column.total > column.jobs.length && (
        <Link to={`/jobs?status=${column.status}`} className={styles.seeAll}>
          See all {column.total.toLocaleString()}
        </Link>
      )}
    </DropZone>
  );
}

export default function BoardPage() {
  const { data: board } = useSuspenseQuery(queries.board());
  const move = useMoveCard();
  const dragging = useDrag((state) => state.dragging);
  const dismissing = useDrag((state) => state.dismissing);
  const askDismiss = useDrag((state) => state.askDismiss);
  const closeDismiss = useDrag((state) => state.closeDismiss);
  return (
    <>
      <PageHeader
        title="Board"
        description="Drag a job that's waiting for your OK to Approved, or to Dismiss."
      />
      <div className={styles.board} role="region" aria-label="Board" tabIndex={0}>
        {board.columns.map((column) => (
          <BoardColumn
            key={column.status}
            column={column}
            onMove={(next) => {
              move.mutate(next);
            }}
          />
        ))}
      </div>
      {canMove(dragging) && (
        <DropZone className={styles.dismiss} label="Dismiss" active onDrop={askDismiss}>
          Drop here to dismiss
        </DropZone>
      )}
      <Dialog
        open={dismissing !== null}
        title={dismissing ? `Dismiss ${dismissing.title}?` : "Dismiss"}
        onClose={closeDismiss}
      >
        {dismissing && (
          <DismissForm
            reasons={board.dismissReasons}
            busy={move.isPending}
            onCancel={closeDismiss}
            onDismiss={(reason) => {
              move.mutate({ job: dismissing, to: "dismissed", reason });
              closeDismiss();
            }}
          />
        )}
      </Dialog>
    </>
  );
}
