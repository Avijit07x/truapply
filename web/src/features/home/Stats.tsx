import type { ComponentType } from "react";
import type { Status, Summary } from "../../api/types";
import { cx } from "../../lib/cx";
import { Link } from "../../lib/router";
import { CountUp } from "../../ui/CountUp";
import { ArrowRight, Clock, type IconProps, Pencil, Pointer, Send } from "../../ui/icons";
import styles from "./Home.module.css";

type Stat = {
  status: Status;
  label: string;
  Icon: ComponentType<IconProps>;
  tone: "warn" | "bad" | "accent" | "good";
};

const STATS: readonly Stat[] = [
  { status: "needs_input", label: "Need your answer", Icon: Pencil, tone: "warn" },
  { status: "finish", label: "Finish these", Icon: Pointer, tone: "bad" },
  { status: "ready", label: "Waiting for your OK", Icon: Clock, tone: "accent" },
  { status: "applied", label: "Applied", Icon: Send, tone: "good" },
];

export function Stats({ counts }: { counts: Summary["counts"] }) {
  return (
    <nav className={styles.stats} aria-label="Where your jobs are">
      {STATS.map(({ status, label, Icon, tone }) => (
        <Link key={status} to={`/jobs?status=${status}`} className={styles.stat}>
          <span className={cx(styles.chip, styles[tone])}>
            <Icon />
          </span>
          <strong className={styles.statCount}>
            <CountUp value={counts[status] ?? 0} />
          </strong>
          <span className={styles.statLabel}>{label}</span>
          <ArrowRight size={12} className={styles.statArrow} />
        </Link>
      ))}
    </nav>
  );
}
