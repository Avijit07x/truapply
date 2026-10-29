import type { RunReport, RunResult } from "../../api/types";
import { cx } from "../../lib/cx";
import { ButtonLink } from "../../ui/Button";
import { Alert, Sliders } from "../../ui/icons";
import { LogView } from "./LogView";
import styles from "./Runs.module.css";

type Row = { title: string; sub: string; pill: string; tone: RunResult["result"] };

const RESULT_LABEL: Record<RunResult["result"], string> = {
  good: "Good match",
  skipped: "Skipped",
  retry: "Will retry",
};

function scoredRow(result: RunResult): Row {
  const label = RESULT_LABEL[result.result];
  return {
    title: result.title,
    sub: result.note ? `${result.company} · ${result.note}` : result.company,
    pill: result.score === null ? label : `${label} · ${String(result.score)}`,
    tone: result.result,
  };
}

function Tile({ value, label, lit = false }: { value: number; label: string; lit?: boolean }) {
  return (
    <div className={cx(styles.tile, lit && value > 0 && styles.lit)}>
      <strong>{value.toLocaleString()}</strong>
      <span>{label}</span>
    </div>
  );
}

function Rows({ title, rows }: { title: string; rows: Row[] }) {
  return (
    <section className={styles.results} aria-label={title}>
      <h3>{title}</h3>
      <ul>
        {rows.map((row, index) => (
          <li key={`${row.title}-${String(index)}`}>
            <strong>{row.title}</strong>
            <small>{row.sub}</small>
            <span className={cx(styles.result, styles[row.tone])}>{row.pill}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function RunReportView({ report, lines }: { report: RunReport; lines: readonly string[] }) {
  const ready = report.prepared.map((job): Row => ({
    title: job.title,
    sub: job.company,
    pill: "Ready",
    tone: "good",
  }));
  return (
    <div className={styles.report}>
      {report.error && (
        <div className={styles.runError} role="alert">
          <Alert size={14} />
          <div>
            <strong>{report.error.message}</strong>
            {report.error.hint && <p>{report.error.hint}</p>}
          </div>
          {report.error.fix && (
            <ButtonLink to={report.error.fix} icon={<Sliders size={14} />}>
              Change it in Settings
            </ButtonLink>
          )}
        </div>
      )}
      <div className={styles.tiles}>
        {report.companies && <Tile value={report.companies.checked} label="companies checked" />}
        {report.jobs && (
          <Tile
            value={report.jobs.fit ?? report.jobs.open}
            label={
              report.jobs.fit === null ? "open jobs checked" : "jobs fit your titles and places"
            }
          />
        )}
        {report.jobs && <Tile value={report.jobs.new} label="new jobs" lit />}
        {report.scored && <Tile value={report.scored.good} label="good matches" lit />}
      </div>
      {ready.length > 0 && <Rows title="Ready for you" rows={ready} />}
      {report.results.length > 0 && (
        <Rows title="Scored this run" rows={report.results.map(scoredRow)} />
      )}
      <details className={styles.fullLog}>
        <summary>Show the full log</summary>
        <LogView lines={lines} />
      </details>
    </div>
  );
}
