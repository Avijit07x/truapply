import type { Status } from "../api/types";
import { STATUS } from "../domain/status";
import { cx } from "../lib/cx";
import styles from "./StatusDot.module.css";

const AUTO_SUBMITTED = "Auto-submitted";

type StatusDotProps = { status: Status; auto?: boolean; labelClassName?: string };

export function StatusDot({ status, auto = false, labelClassName }: StatusDotProps) {
  const { tone } = STATUS[status];
  const label = auto && status === "applied" ? AUTO_SUBMITTED : STATUS[status].label;
  return (
    <span className={styles.status} title={label}>
      <span className={cx(styles.dot, styles[tone])} aria-hidden="true" />
      <span className={cx(styles.label, labelClassName)}>{label}</span>
    </span>
  );
}
