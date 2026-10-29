import type { Group, Workflow } from "../../api/types";
import { cx } from "../../lib/cx";
import { Link } from "../../lib/router";
import { CountUp } from "../../ui/CountUp";
import styles from "./Home.module.css";

const STAGES: readonly { group: Group; label: string; fill: string | undefined }[] = [
  { group: "not_a_fit", label: "Not a fit", fill: styles.fillQuiet },
  { group: "scored", label: "Good matches", fill: styles.fillSoft },
  { group: "ready", label: "Ready for you", fill: styles.fillAccent },
  { group: "applied", label: "Applied", fill: styles.fillGood },
];

function share(part: number, whole: number): string {
  return `${String(whole > 0 ? (part / whole) * 100 : 0)}%`;
}

export function Pipeline({ groups }: { groups: Workflow["groups"] }) {
  const found = groups.found;
  return (
    <section className={styles.block} aria-labelledby="pipeline-title">
      <header className={styles.blockHead}>
        <h2 id="pipeline-title" className={styles.blockTitle}>
          Pipeline
        </h2>
      </header>
      <ul className={styles.stats}>
        <li>
          <Link to="/jobs?group=found" className={styles.stat}>
            <span className={styles.statCount}>
              <CountUp value={found} />
            </span>
            <span className={styles.statLabel}>Found</span>
          </Link>
        </li>
        {STAGES.map(({ group, label, fill }) => (
          <li key={group}>
            <Link to={`/jobs?group=${group}`} className={styles.stat}>
              <span className={styles.statCount}>
                <CountUp value={groups[group]} />
              </span>
              <span className={styles.statLabel}>
                <span className={cx(styles.swatch, fill)} />
                {label}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <div className={styles.bar} aria-hidden="true">
        {STAGES.map(({ group, fill }) => (
          <span
            key={group}
            className={cx(styles.segment, fill)}
            style={{ width: share(groups[group], found) }}
          />
        ))}
      </div>
      {found === 0 && (
        <p className={styles.barNote}>
          No jobs yet. Press Run now, and this fills in as jobs are found, scored and applied to.
        </p>
      )}
    </section>
  );
}
