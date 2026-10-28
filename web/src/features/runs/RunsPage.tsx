import { useSuspenseQuery } from "@tanstack/react-query";
import { useRunStop } from "../../api/mutations";
import { queries } from "../../api/queries";
import type { RunKind, RunLog, RunState } from "../../api/types";
import { cx } from "../../lib/cx";
import { when } from "../../lib/format";
import { Ago } from "../../ui/Ago";
import { Link } from "../../lib/router";
import { PageHeader, Row } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Alert, ArrowRight, Check, Clock, Stop } from "../../ui/icons";
import { Spinner } from "../../ui/Spinner";
import { toast } from "../../ui/toasts";
import { LogView } from "./LogView";
import { RunForm } from "./RunForm";
import styles from "./Runs.module.css";

function outcome(code: number | null): string {
  if (code === 0) {
    return "Finished.";
  }
  if (code !== null && code < 0) {
    return "Stopped before it finished.";
  }
  return `Ended with an error (code ${String(code)}). The log says what went wrong.`;
}

function Progress({ run }: { run: RunState }) {
  const stop = useRunStop();
  return (
    <section className={styles.block} aria-labelledby="running-title">
      <h2 id="running-title" className={styles.blockTitle}>
        Running now
      </h2>
      <p className={styles.live}>
        <span className={styles.pip} aria-hidden="true" />
        Started {when(run.startedAt)}
      </p>
      {run.stoppable && (
        <Row>
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
        </Row>
      )}
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
    <li>
      <div className={cx(styles.logRow, styles.next)}>
        <span className={styles.runIcon} role="img" aria-label="Starts next">
          <Clock size={12} />
        </span>
        <time dateTime={at}>{when(at)}</time>
        <span className={cx(styles.kind, styles.automatic)}>{KIND_LABEL.automatic}</span>
        <span className={styles.ago}>
          <Ago iso={at} past="Starting soon" />
        </span>
        <span />
      </div>
    </li>
  );
}

function RecentRuns({ logs, next }: { logs: readonly RunLog[]; next: string | null }) {
  if (logs.length === 0 && !next) {
    return null;
  }
  return (
    <section className={styles.block} aria-labelledby="recent-title">
      <h2 id="recent-title" className={styles.blockTitle}>
        Recent runs
      </h2>
      <ul className={styles.runs}>
        {next && <NextRun at={next} />}
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

function state(run: RunState): string {
  if (run.running) {
    return "Updates every few seconds.";
  }
  return run.exitCode === null ? "" : outcome(run.exitCode);
}

function SavedLog({ name }: { name: string }) {
  const { data: log } = useSuspenseQuery(queries.runLog(name));
  return <LogView lines={log.lines} />;
}

function Output({ run }: { run: RunState }) {
  const latest = run.logs[0];
  const live = run.running || run.log.length > 0 || !latest;
  return (
    <section className={styles.output} aria-labelledby="log-title">
      <header className={styles.outputHead}>
        <h2 id="log-title" className={styles.blockTitle}>
          {run.running ? "Live log" : "Last run"}
        </h2>
        <span className={styles.outputState}>
          {live ? state(run) : `Finished ${when(latest.finishedAt)}`}
        </span>
      </header>
      {live ? (
        <LogView
          lines={run.log}
          empty={run.running ? "Starting..." : "No runs yet. Start one on the left."}
        />
      ) : (
        <SavedLog name={latest.name} />
      )}
    </section>
  );
}

export default function RunsPage() {
  const { data: run } = useSuspenseQuery(queries.runs());
  return (
    <div className={styles.page}>
      <PageHeader
        title="Run"
        description="Finds new jobs, scores them and tailors your resume for the good ones. Nothing is sent unless auto-submit is on."
      />
      <div className={styles.console}>
        <div className={styles.controls}>
          {run.running ? <Progress run={run} /> : <RunForm limits={run.limits} />}
          <RecentRuns logs={run.logs} next={run.nextAutomatic} />
        </div>
        <Output run={run} />
      </div>
    </div>
  );
}
