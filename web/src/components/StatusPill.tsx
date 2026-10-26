import type { Status } from "../api/types";
import { STATUS } from "../domain/status";
import { cx } from "../lib/cx";
import styles from "./StatusPill.module.css";

export function StatusPill({ status }: { status: Status }) {
  const { label, tone } = STATUS[status];
  return <span className={cx(styles.pill, styles[tone])}>{label}</span>;
}
