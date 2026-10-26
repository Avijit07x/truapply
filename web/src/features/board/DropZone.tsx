import { type DragEvent, type ReactNode, useState } from "react";
import type { JobRow } from "../../api/types";
import { cx } from "../../lib/cx";
import styles from "./Board.module.css";
import { canMove, useDrag } from "./dragStore";

type DropZoneProps = {
  active: boolean;
  onDrop: (job: JobRow) => void;
  className?: string | undefined;
  label?: string;
  children: ReactNode;
};

export function DropZone({ active, onDrop, className, label, children }: DropZoneProps) {
  const dragging = useDrag((state) => state.dragging);
  const [over, setOver] = useState(false);
  const accepts = active && canMove(dragging);
  const hover = (event: DragEvent<HTMLElement>) => {
    if (!accepts) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    setOver(true);
  };
  return (
    <section
      aria-label={label}
      className={cx(className, accepts && styles.accepts, accepts && over && styles.over)}
      onDragEnter={hover}
      onDragOver={hover}
      onDragLeave={() => {
        setOver(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        if (accepts) {
          onDrop(dragging);
        }
      }}
    >
      {children}
    </section>
  );
}
