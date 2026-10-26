import { create } from "zustand";
import type { JobRow } from "../../api/types";

type DragState = {
  dragging: JobRow | null;
  dismissing: JobRow | null;
  startDrag: (job: JobRow) => void;
  endDrag: () => void;
  askDismiss: (job: JobRow) => void;
  closeDismiss: () => void;
};

export const useDrag = create<DragState>()((set) => ({
  dragging: null,
  dismissing: null,
  startDrag: (job) => {
    set({ dragging: job });
  },
  endDrag: () => {
    set({ dragging: null });
  },
  askDismiss: (job) => {
    set({ dragging: null, dismissing: job });
  },
  closeDismiss: () => {
    set({ dismissing: null });
  },
}));

export function canMove(job: JobRow | null): job is JobRow {
  return job?.status === "ready";
}
