import { useSuspenseQuery } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import type { Column, Status } from "../../api/types";
import { DismissForm } from "../../components/DismissForm";
import { STATUS } from "../../domain/status";
import { cx } from "../../lib/cx";
import { Link } from "../../lib/router";
import { PageHeader } from "../../ui/Blocks";
import { Dialog } from "../../ui/Dialog";
import { ArrowRight, Check, Close } from "../../ui/icons";
import styles from "./Board.module.css";
import { BoardCard } from "./BoardCard";
import { DropZone } from "./DropZone";
import { canMove, useDrag } from "./dragStore";
import { type Move, useMoveCard } from "./useMoveCard";

type Lane = { name: string; tone: "plain" | "warn" | "bad" | "accent" | "good"; empty: string };

const LANES: Partial<Record<Status, Lane>> = {
  scored: { name: "Good matches to tailor", tone: "plain", empty: "No good matches waiting." },
  ready: { name: "Ready for you to apply", tone: "accent", empty: "Nothing ready yet." },
  applied: { name: "Applied", tone: "good", empty: "Drag a job here once you submitted it." },
};

function laneOf(status: Status): Lane {
  return LANES[status] ?? { name: STATUS[status].label, tone: "plain", empty: "Nothing here." };
}

function BoardColumn({ column, onMove }: { column: Column; onMove: (move: Move) => void }) {
  const { name, tone, empty } = laneOf(column.status);
  return (
    <DropZone
      className={styles.column}
      label={name}
      active={column.status === "applied"}
      onDrop={(job) => {
        onMove({ job, to: "applied" });
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
        {column.jobs.length === 0 && <p className={styles.empty}>{empty}</p>}
      </div>
      {column.total > column.jobs.length && (
        <Link to={`/jobs?status=${column.status}`} className={styles.seeAll}>
          See all {column.total.toLocaleString()}
          <ArrowRight size={12} />
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
    <div className={styles.page}>
      <PageHeader
        title="Board"
        description="Drag a job you submitted to Applied, or one you don't want to Dismiss."
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
        <div className={styles.dock}>
          <DropZone
            className={cx(styles.target, styles.appliedTarget)}
            label="I submitted it"
            active
            onDrop={(job) => {
              move.mutate({ job, to: "applied" });
            }}
          >
            <Check size={14} />
            Drop when you submitted it
          </DropZone>
          <DropZone
            className={cx(styles.target, styles.dismissTarget)}
            label="Dismiss"
            active
            onDrop={askDismiss}
          >
            <Close size={14} />
            Drop to dismiss
          </DropZone>
        </div>
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
    </div>
  );
}
