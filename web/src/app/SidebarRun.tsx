import { useRunStart } from "../api/mutations";
import type { RunStage, RunState } from "../api/types";
import { cx } from "../lib/cx";
import { Link } from "../lib/router";
import { Ago, Elapsed } from "../ui/Ago";
import { Button } from "../ui/Button";
import { Alert, ArrowRight, Play } from "../ui/icons";
import { toast } from "../ui/toasts";
import styles from "./Layout.module.css";

const STAGES: readonly RunStage[] = ["find", "score", "tailor"];

const STAGE_LABEL: Record<RunStage, string> = {
  find: "Finding",
  score: "Scoring",
  tailor: "Tailoring",
};

function lastLine(log: readonly string[]): string {
  return (
    [...log]
      .reverse()
      .find((line) => line.trim() !== "")
      ?.trim() ?? ""
  );
}

function Running({ run }: { run: RunState }) {
  const current = STAGES.indexOf(run.stage ?? "find");
  return (
    <Link
      to="/runs"
      className={cx(styles.runCard, styles.runLive)}
      title="Nothing is sent. Watch it on Activity."
    >
      <span className={styles.runTop}>
        <span className={styles.pip} aria-hidden="true" />
        Running
        {run.startedAt && (
          <span className={styles.runTime}>
            <Elapsed iso={run.startedAt} />
          </span>
        )}
      </span>
      <span className={styles.runSteps}>
        {STAGES.map((stage, index) => (
          <span
            key={stage}
            className={cx(index < current && styles.stepDone, index === current && styles.stepNow)}
            aria-current={index === current ? "step" : undefined}
          >
            <b aria-hidden="true" />
            {STAGE_LABEL[stage]}
          </span>
        ))}
      </span>
      <span className={styles.runLine}>{lastLine(run.log)}</span>
    </Link>
  );
}

function When({ run }: { run: RunState }) {
  if (run.nextAutomatic) {
    return (
      <>
        Next run <Ago iso={run.nextAutomatic} past="starting soon" />
      </>
    );
  }
  const last = run.logs[0];
  return last ? (
    <>
      Last run <Ago iso={last.finishedAt} />
    </>
  ) : (
    "No runs yet"
  );
}

export function SidebarRun({ run, here }: { run: RunState; here: boolean }) {
  const start = useRunStart();
  if (run.running) {
    return <Running run={run} />;
  }
  const problem = run.logs[0]?.problem;
  return (
    <div className={styles.runCard}>
      {problem && (
        <Link to="/runs" className={styles.runProblem} title={problem}>
          <Alert size={13} />
          Last run stopped
          <ArrowRight size={12} />
        </Link>
      )}
      <span className={styles.runTop}>
        <span className={styles.pip} aria-hidden="true" />
        <span>
          <When run={run} />
        </span>
      </span>
      {!here && (
        <Button
          variant="primary"
          icon={<Play size={12} />}
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
      )}
    </div>
  );
}
