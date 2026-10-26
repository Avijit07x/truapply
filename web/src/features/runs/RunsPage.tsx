import { useSuspenseQuery } from "@tanstack/react-query";
import { useRunStop } from "../../api/mutations";
import { queries } from "../../api/queries";
import type { RunLog, RunState } from "../../api/types";
import { when } from "../../lib/format";
import { Link } from "../../lib/router";
import { List, Note, PageHeader, Row, Section, Stack } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { ArrowRight, Stop } from "../../ui/icons";
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
    <Section title="Running now">
      <Stack>
        <Row>
          <span className={styles.live}>
            <span className={styles.pip} aria-hidden="true" />
            Started {when(run.startedAt)}
          </span>
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
        <LogView lines={run.log} />
      </Stack>
    </Section>
  );
}

function RecentRuns({ logs }: { logs: readonly RunLog[] }) {
  if (logs.length === 0) {
    return null;
  }
  return (
    <Section title="Recent runs">
      <List>
        {logs.map((log) => (
          <li key={log.name}>
            <Link to={`/runs/${log.name}`} className={styles.logRow}>
              <time dateTime={log.finishedAt}>{when(log.finishedAt)}</time>
              <ArrowRight size={12} />
            </Link>
          </li>
        ))}
      </List>
    </Section>
  );
}

export default function RunsPage() {
  const { data: run } = useSuspenseQuery(queries.runs());
  return (
    <div className={styles.page}>
      <PageHeader
        title="Run"
        description="Finds new jobs, scores them, fills forms, and sends the jobs you approved."
      />
      {run.running ? <Progress run={run} /> : <RunForm limits={run.limits} />}
      {!run.running && run.exitCode !== null && (
        <Section title="Last run">
          <Stack>
            <Note>{outcome(run.exitCode)}</Note>
            <LogView lines={run.log} />
          </Stack>
        </Section>
      )}
      <RecentRuns logs={run.logs} />
    </div>
  );
}
