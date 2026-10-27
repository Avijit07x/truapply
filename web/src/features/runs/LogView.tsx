import styles from "./Runs.module.css";

type LogViewProps = { lines: readonly string[]; empty?: string };

export function LogView({ lines, empty = "Nothing written yet." }: LogViewProps) {
  if (lines.length === 0) {
    return <p className={styles.logEmpty}>{empty}</p>;
  }
  return (
    <div className={styles.log} tabIndex={0} aria-label="Run log">
      <pre>{lines.join("\n")}</pre>
    </div>
  );
}
