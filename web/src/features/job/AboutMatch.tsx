import { Toggle } from "@base-ui/react/toggle";
import { ToggleGroup } from "@base-ui/react/toggle-group";
import { useJobChange } from "../../api/mutations";
import type { JobDetail } from "../../api/types";
import styles from "./Job.module.css";

function MatchFeedback({ job }: { job: JobDetail }) {
  const change = useJobChange(job.id);
  return (
    <section className={styles.sideSection} aria-labelledby="match-title">
      <h2 id="match-title" className={styles.sideTitle}>
        Was it a good match?
      </h2>
      <ToggleGroup
        className={styles.toggles}
        value={job.feedback === 0 ? [] : [String(job.feedback)]}
        disabled={change.isPending}
        onValueChange={(value) => {
          const picked = value[0];
          if (picked) {
            change.mutate({ action: "thumbs", body: { value: Number(picked) } });
          }
        }}
      >
        <Toggle value="1" className={styles.toggle}>
          Good match
        </Toggle>
        <Toggle value="-1" className={styles.toggle}>
          Bad match
        </Toggle>
      </ToggleGroup>
      <p className={styles.sideNote}>Teaches the scorer.</p>
    </section>
  );
}

export function AboutMatch({ job }: { job: JobDetail }) {
  const lastStep = job.note && job.note !== job.reason ? job.note : "";
  return (
    <aside className={styles.side} aria-label="About this match">
      {job.reason && (
        <section className={styles.sideSection} aria-labelledby="why-title">
          <h2 id="why-title" className={styles.sideTitle}>
            Why this score
          </h2>
          <p className={styles.sideText}>{job.reason}</p>
        </section>
      )}
      {job.actions.includes("thumbs") && <MatchFeedback job={job} />}
      {lastStep && (
        <section className={styles.sideSection} aria-labelledby="step-title">
          <h2 id="step-title" className={styles.sideTitle}>
            Last step
          </h2>
          <p className={styles.sideText}>{lastStep}</p>
        </section>
      )}
    </aside>
  );
}
