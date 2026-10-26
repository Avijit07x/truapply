import { useRunStart } from "../../api/mutations";
import type { RunState, Status, Summary } from "../../api/types";
import { plural, when } from "../../lib/format";
import { Button, ButtonLink } from "../../ui/Button";
import { Play } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import styles from "./Home.module.css";

const WAITING: readonly Status[] = ["needs_input", "finish", "ready"];
const NOON = 12;
const EVENING = 18;

function greeting(hour: number): string {
  if (hour < NOON) {
    return "Good morning";
  }
  return hour < EVENING ? "Good afternoon" : "Good evening";
}

function waitingNote(count: number): string {
  if (count === 0) {
    return "Nothing needs you right now";
  }
  return count === 1 ? "1 job needs you" : `${plural(count, "job")} need you`;
}

function runNote(run: RunState): string {
  if (run.running) {
    return `Running since ${when(run.startedAt)}`;
  }
  const last = run.logs[0];
  return last ? `Last run ${when(last.finishedAt)}` : "No runs yet";
}

export function Hero({ summary }: { summary: Summary }) {
  const start = useRunStart();
  const { run } = summary;
  const waiting = WAITING.reduce((total, status) => total + (summary.counts[status] ?? 0), 0);
  return (
    <header className={styles.hero}>
      <div className={styles.heroText}>
        <h1 className={styles.greeting}>{greeting(new Date().getHours())}</h1>
        <p className={styles.heroNote}>
          <span>{waitingNote(waiting)}</span>
          <span aria-hidden="true">·</span>
          <span className={run.running ? styles.live : undefined}>{runNote(run)}</span>
          <span aria-hidden="true">·</span>
          <span>{plural(summary.total, "job")} found</span>
        </p>
      </div>
      <div className={styles.heroActions}>
        {run.running ? (
          <ButtonLink to="/runs" variant="primary">
            See progress
          </ButtonLink>
        ) : (
          <Button
            variant="primary"
            icon={<Play size={14} />}
            busy={start.isPending}
            title="A dry run: forms are filled in, nothing is sent"
            onClick={() => {
              start.mutate(
                { limit: run.limits.default, search: true, send: false },
                {
                  onSuccess: () => {
                    toast("Run started. It's a dry run, nothing is sent.");
                  },
                },
              );
            }}
          >
            Run now
          </Button>
        )}
        <ButtonLink to="/runs" variant="ghost">
          More options
        </ButtonLink>
      </div>
    </header>
  );
}
