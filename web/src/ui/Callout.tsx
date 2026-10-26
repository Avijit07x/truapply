import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import styles from "./Callout.module.css";
import { Alert } from "./icons";

type CalloutProps = { tone?: "info" | "bad"; icon?: ReactNode; children: ReactNode };

export function Callout({ tone = "info", icon = <Alert />, children }: CalloutProps) {
  return (
    <div className={cx(styles.callout, styles[tone])} role={tone === "bad" ? "alert" : undefined}>
      <span className={styles.icon}>{icon}</span>
      <div className={styles.body}>{children}</div>
    </div>
  );
}
