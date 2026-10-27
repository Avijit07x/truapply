import type { Status } from "../api/types";
import { STATUS } from "../domain/status";
import { cx } from "../lib/cx";
import styles from "./StatusDot.module.css";

export function StatusDot({ status, labelClassName }: { status: Status; labelClassName?: string }) {
  const { label, tone } = STATUS[status];
  return (
    <span className={styles.status} title={label}>
      <span className={cx(styles.dot, styles[tone])} aria-hidden="true" />
      <span className={cx(styles.label, labelClassName)}>{label}</span>
    </span>
  );
}
