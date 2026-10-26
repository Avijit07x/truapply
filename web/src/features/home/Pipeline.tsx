import type { Group, Workflow } from "../../api/types";
import { cx } from "../../lib/cx";
import { Link } from "../../lib/router";
import { Card, Note } from "../../ui/Blocks";
import { CountUp } from "../../ui/CountUp";
import { ArrowRight } from "../../ui/icons";
import styles from "./Home.module.css";

const STAGES: readonly { group: Group; label: string; quiet?: boolean }[] = [
  { group: "found", label: "Found" },
  { group: "not_a_fit", label: "Not a fit", quiet: true },
  { group: "scored", label: "Good matches to fill" },
  { group: "ready", label: "Waiting for your OK" },
  { group: "applied", label: "Applied" },
];

export function Pipeline({ groups }: { groups: Workflow["groups"] }) {
  const most = Math.max(groups.found, 1);
  return (
    <Card title="Pipeline">
      <Note>Where your jobs are now.</Note>
      <ul className={styles.stages}>
        {STAGES.map(({ group, label, quiet = false }) => (
          <li key={group}>
            <Link to={`/jobs?group=${group}`} className={styles.stage}>
              <span className={styles.stageLabel}>{label}</span>
              <span className={styles.stageCount}>
                <CountUp value={groups[group]} />
              </span>
              <span className={styles.track} aria-hidden="true">
                <span
                  className={cx(styles.fill, quiet && styles.quiet)}
                  style={{ width: `${String((groups[group] / most) * 100)}%` }}
                />
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <Link to="/workflow" className={styles.more}>
        Open the workflow map
        <ArrowRight size={12} />
      </Link>
    </Card>
  );
}
