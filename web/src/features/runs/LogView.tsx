import { Empty } from "../../ui/Blocks";
import styles from "./Runs.module.css";

export function LogView({ lines }: { lines: readonly string[] }) {
  if (lines.length === 0) {
    return <Empty>Nothing written yet.</Empty>;
  }
  return (
    <div className={styles.log} tabIndex={0} aria-label="Run log">
      <pre>{lines.join("\n")}</pre>
    </div>
  );
}
