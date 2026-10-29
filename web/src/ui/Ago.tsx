import { useSyncExternalStore } from "react";
import { ago, elapsed, isPast } from "../lib/format";

const TICK_MS = 1_000;

const listeners = new Set<() => void>();
let timer: ReturnType<typeof setInterval> | undefined;

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  timer ??= setInterval(() => {
    for (const notify of listeners) {
      notify();
    }
  }, TICK_MS);
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) {
      clearInterval(timer);
      timer = undefined;
    }
  };
}

export function Ago({ iso, past }: { iso: string; past?: string }) {
  return useSyncExternalStore(subscribe, () =>
    past !== undefined && isPast(iso) ? past : ago(iso),
  );
}

export function Elapsed({ iso }: { iso: string }) {
  return useSyncExternalStore(subscribe, () => elapsed(iso));
}
