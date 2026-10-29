import { useSuspenseQuery } from "@tanstack/react-query";
import { useRunStop } from "../../api/mutations";
import { queries } from "../../api/queries";
import type { RunKind, RunLog, RunStage, RunState } from "../../api/types";
import { cx } from "../../lib/cx";
import { when } from "../../lib/format";
import { Ago } from "../../ui/Ago";
import { Link } from "../../lib/router";
import { PageHeader } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Alert, ArrowRight, Check, Clock, Stop } from "../../ui/icons";
import { Spinner } from "../../ui/Spinner";
import { toast } from "../../ui/toasts";
import { LogView } from "./LogView";
import { RunReportView } from "./RunReport";
import { RunForm } from "./RunForm";
import styles from "./Runs.module.css";

const STEPS: readonly { stage: RunStage; label: string }[] = [
  { stage: "find", label: "Find jobs" },
  { stage: "score", label: "Score" },
  { stage: "tailor", label: "Tailor" },
];

function stepState(at: number, now: number): { look: string | undefined; text: string } {
  if (now < 0 || at > now) return { look: undefined, text: "Waiting" };
  return at < now
    ? { look: styles.stepDone, text: "Done" }
    : { look: styles.stepOn, text: "Working" };
}

function Progress({ run }: { run: RunState }) {
  const stop = useRunStop();
  const now = run.stage ? STEPS.findIndex((step) => step.stage === run.stage) : -1;
  return (
    <section className={styles.card} aria-labelledby="running-title">
      <header className={styles.cardHead}>
        <h2 id="running-title" className={styles.blockTitle}>
          Running now
        </h2>
        <p className={styles.live}>
          <span className={styles.pip} aria-hidden="true" />
          Started {when(run.startedAt)}
        </p>
        {run.stoppable && (
          <Button
            variant="danger"
            icon={<Stop size={14} />}
            busy={stop.isPending}
            onClick={() => {
              stop.mutate(undefined, {
                onSuccess: () => {
                  toast("Run stopped.");
                },
              });
            }}
          >
            Stop
          </Button>
        )}
      </header>
      <ol className={styles.steps}>
        {STEPS.map((step, at) => {
          const { look, text } = stepState(at, now);
          return (
            <li key={step.stage} className={cx(styles.step, look)}>
              <strong>{step.label}</strong>
              {text}
            </li>
          );
        })}
      </ol>
      <LogView lines={run.log} empty="Starting..." />
    </section>
  );
}

const ENDED: Record<NonNullable<RunLog["outcome"]>, { Icon: typeof Check; label: string }> = {
  done: { Icon: Check, label: "Finished" },
  failed: { Icon: Alert, label: "Ended with an error" },
  stopped: { Icon: Stop, label: "Stopped before it finished" },
};

function RunIcon({ log }: { log: RunLog }) {
  if (log.running || !log.outcome) {
    return (
      <span className={styles.runIcon} role="img" aria-label="Running now">
        <Spinner />
      </span>
    );
  }
  const { Icon, label } = ENDED[log.outcome];
  return (
    <span className={cx(styles.runIcon, styles[log.outcome])} role="img" aria-label={label}>
      <Icon size={12} />
    </span>
  );
}

function NextRun({ at }: { at: string }) {
  return (
    <section className={styles.nextRun} aria-labelledby="next-title">
      <Clock size={14} />
      <h2 id="next-title" className={styles.blockTitle}>
        Next automatic run
      </h2>
      <span className={styles.ago}>
        <time dateTime={at}>{when(at)}</time> · <Ago iso={at} past="starting soon" />
      </span>
      <Link to="/settings?tab=automation" className={styles.change}>
        Change
        <ArrowRight size={12} />
      </Link>
    </section>
  );
}

function RecentRuns({ logs }: { logs: readonly RunLog[] }) {
  if (logs.length === 0) {
    return null;
  }
  return (
    <section className={styles.block} aria-labelledby="recent-title">
      <h2 id="recent-title" className={styles.blockTitle}>
        Recent runs
      </h2>
      <ul className={styles.runs}>
        {logs.map((log) => (
          <li key={log.name}>
            <Link to={`/runs/${log.name}`} className={styles.logRow}>
              <RunIcon log={log} />
              <time dateTime={log.finishedAt}>{when(log.finishedAt)}</time>
              {log.kind ? (
                <span className={cx(styles.kind, log.kind === "automatic" && styles.automatic)}>
                  {KIND_LABEL[log.kind]}
                </span>
              ) : (
                <span />
              )}
              <span className={styles.ago}>
                {log.running ? "Running now" : <Ago iso={log.finishedAt} />}
              </span>
              <ArrowRight size={12} />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

const KIND_LABEL: Record<RunKind, string> = { automatic: "Automatic", manual: "Manual" };

function SavedLog({ name }: { name: string }) {
  const { data: log } = useSuspenseQuery(queries.runLog(name));
  return log.report ? (
    <RunReportView report={log.report} lines={log.lines} />
  ) : (
    <LogView lines={log.lines} />
  );
}

function LastRun({ run }: { run: RunState }) {
  const latest = run.logs[0];
  if (run.running) {
    return null;
  }
  if (!latest) {
    return (
      <div className={styles.logEmpty}>
        <strong>No runs yet</strong>
        Press Run now to find new jobs, score them and tailor your resume. Nothing is sent.
      </div>
    );
  }
  return (
    <section className={styles.block} aria-labelledby="log-title">
      <header className={styles.outputHead}>
        <h2 id="log-title" className={styles.blockTitle}>
          Last run
        </h2>
        <span className={styles.outputState}>
          <RunIcon log={latest} />
          {latest.outcome ? ENDED[latest.outcome].label : "Finished"} · {when(latest.finishedAt)}
        </span>
      </header>
      <SavedLog name={latest.name} />
    </section>
  );
}

export default function RunsPage() {
  const { data: run } = useSuspenseQuery(queries.runs());
  return (
    <>
      <PageHeader
        title="Activity"
        description="Each run finds new jobs, scores them and tailors your resume for the good ones. Nothing is sent unless auto-submit is on."
      />
      <div className={styles.page}>
        {run.running ? <Progress run={run} /> : <RunForm limits={run.limits} />}
        {run.nextAutomatic && <NextRun at={run.nextAutomatic} />}
        <RecentRuns logs={run.logs} />
        <LastRun run={run} />
      </div>
    </>
  );
}
