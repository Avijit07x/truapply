import { useLayoutEffect, useRef } from "react";
import { prefersLessMotion } from "../lib/motion";

const DURATION_MS = 700;

function eased(progress: number): number {
  return 1 - (1 - progress) ** 3;
}

export function CountUp({ value }: { value: number }) {
  const node = useRef<HTMLSpanElement>(null);
  const shown = useRef(0);
  useLayoutEffect(() => {
    const target = node.current;
    const from = shown.current;
    if (!target || from === value || prefersLessMotion()) {
      shown.current = value;
      return;
    }
    const start = performance.now();
    let frame = 0;
    const step = (now: number) => {
      const progress = Math.min((now - start) / DURATION_MS, 1);
      shown.current = Math.round(from + (value - from) * eased(progress));
      target.textContent = shown.current.toLocaleString();
      if (progress < 1) {
        frame = requestAnimationFrame(step);
      }
    };
    target.textContent = from.toLocaleString();
    frame = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(frame);
    };
  }, [value]);
  return <span ref={node}>{value.toLocaleString()}</span>;
}
