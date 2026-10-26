import { cx } from "../lib/cx";
import styles from "./PageSkeleton.module.css";

export function PageSkeleton() {
  return (
    <div className={styles.skeleton} aria-busy="true" aria-label="Loading">
      <span className={cx(styles.bar, styles.heading)} />
      <span className={styles.bar} />
      <span className={styles.block} />
      <span className={styles.block} />
    </div>
  );
}
