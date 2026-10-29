import { useRunStart } from "../api/mutations";
import type { RunStage, RunState } from "../api/types";
import { cx } from "../lib/cx";
import { Link } from "../lib/router";
import { Ago } from "../ui/Ago";
import { Button } from "../ui/Button";
import { Alert, ArrowRight, Play } from "../ui/icons";
import { toast } from "../ui/toasts";
import styles from "./Layout.module.css";

const STAGES: readonly RunStage[] = ["find", "score", "tailor"];

const STAGE_LABEL: Record<RunStage, string> = {
  find: "Finding jobs",
  score: "Scoring",
  tailor: "Tailoring",
};

function Running({ stage }: { stage: RunStage | null }) {
  const done = stage ? STAGES.indexOf(stage) + 1 : 0;
  return (
    <Link to="/runs" className={cx(styles.runCard, styles.runLive)}>
      <span className={styles.runTop}>
        <span className={styles.pip} aria-hidden="true" />
        Running{stage ? ` · ${STAGE_LABEL[stage]}` : ""}
      </span>
      <span className={styles.runBar} aria-hidden="true">
        <span style={{ width: `${String(Math.max(8, (done / STAGES.length) * 100))}%` }} />
      </span>
      <span className={styles.runSub}>Nothing is sent. Watch it on Activity.</span>
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
    return <Running stage={run.stage} />;
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
