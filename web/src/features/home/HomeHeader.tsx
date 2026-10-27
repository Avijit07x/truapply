import { useRunStart } from "../../api/mutations";
import type { RunState, Summary } from "../../api/types";
import { plural, when } from "../../lib/format";
import { Row } from "../../ui/Blocks";
import { Button, ButtonLink } from "../../ui/Button";
import { Play } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import styles from "./Home.module.css";

function headline(count: number): string {
  if (count === 0) {
    return "You're all caught up";
  }
  return count === 1 ? "1 job is ready for you" : `${plural(count, "job")} are ready for you`;
}

function runNote(run: RunState): string {
  if (run.running) {
    return `Running since ${when(run.startedAt)}`;
  }
  const last = run.logs[0];
  return last ? `Last run ${when(last.finishedAt)}` : "No runs yet";
}

function RunButton({ run }: { run: RunState }) {
  const start = useRunStart();
  if (run.running) {
    return (
      <ButtonLink to="/runs" variant="primary">
        See progress
      </ButtonLink>
    );
  }
  return (
    <Button
      variant="primary"
      icon={<Play size={14} />}
      busy={start.isPending}
      title="Finds, scores and tailors new jobs. Nothing is sent."
      onClick={() => {
        start.mutate(
          { limit: run.limits.default, search: true },
          {
            onSuccess: () => {
              toast("Run started. Nothing is sent.");
            },
          },
        );
      }}
    >
      Run now
    </Button>
  );
}

export function HomeHeader({ summary }: { summary: Summary }) {
  const { run, counts } = summary;
  const waiting = counts.ready ?? 0;
  return (
    <header className={styles.header}>
      <div className={styles.headline}>
        <h1 className={styles.title}>{headline(waiting)}</h1>
        <p className={styles.facts}>
          <span className={run.running ? styles.live : undefined}>{runNote(run)}</span>
          <span>{plural(summary.total, "job")} found</span>
          <span>{(counts.applied ?? 0).toLocaleString()} applied</span>
        </p>
      </div>
      <Row>
        <RunButton run={run} />
        <ButtonLink to="/runs" variant="ghost">
          More options
        </ButtonLink>
      </Row>
    </header>
  );
}
