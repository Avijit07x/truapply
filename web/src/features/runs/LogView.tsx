import type { ReactNode } from "react";
import styles from "./Runs.module.css";

type LogViewProps = { lines: readonly string[]; empty?: ReactNode };

export function LogView({ lines, empty = "Nothing written yet." }: LogViewProps) {
  if (lines.length === 0) {
    return <div className={styles.logEmpty}>{empty}</div>;
  }
  return (
    <div className={styles.log} tabIndex={0} aria-label="Run log">
      <pre>{lines.join("\n")}</pre>
    </div>
  );
}
