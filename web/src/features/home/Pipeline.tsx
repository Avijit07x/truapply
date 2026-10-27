import type { Group, Workflow } from "../../api/types";
import { cx } from "../../lib/cx";
import { Link } from "../../lib/router";
import { CountUp } from "../../ui/CountUp";
import { ArrowRight } from "../../ui/icons";
import styles from "./Home.module.css";

const STAGES: readonly { group: Group; label: string; fill: string | undefined }[] = [
  { group: "not_a_fit", label: "Not a fit", fill: styles.fillQuiet },
  { group: "scored", label: "Good matches to tailor", fill: styles.fillSoft },
  { group: "ready", label: "Ready for you to apply", fill: styles.fillAccent },
  { group: "applied", label: "Applied", fill: styles.fillGood },
];

function share(part: number, whole: number): string {
  return `${String(whole > 0 ? (part / whole) * 100 : 0)}%`;
}

export function Pipeline({ groups }: { groups: Workflow["groups"] }) {
  const found = groups.found;
  return (
    <section className={styles.railSection} aria-labelledby="pipeline-title">
      <header className={styles.railHead}>
        <h2 id="pipeline-title" className={styles.railTitle}>
          Pipeline
        </h2>
        <Link to="/workflow" className={styles.railLink}>
          Map
          <ArrowRight size={12} />
        </Link>
      </header>
      <div className={styles.bar} aria-hidden="true">
        {STAGES.map(({ group, fill }) => (
          <span
            key={group}
            className={cx(styles.segment, fill)}
            style={{ width: share(groups[group], found) }}
          />
        ))}
      </div>
      <ul className={styles.stages}>
        <li>
          <Link to="/jobs?group=found" className={styles.stage}>
            <span />
            <span className={styles.stageLabel}>Found</span>
            <span className={styles.stageCount}>
              <CountUp value={found} />
            </span>
          </Link>
        </li>
        {STAGES.map(({ group, label, fill }) => (
          <li key={group}>
            <Link to={`/jobs?group=${group}`} className={styles.stage}>
              <span className={cx(styles.swatch, fill)} />
              <span className={styles.stageLabel}>{label}</span>
              <span className={styles.stageCount}>
                <CountUp value={groups[group]} />
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
