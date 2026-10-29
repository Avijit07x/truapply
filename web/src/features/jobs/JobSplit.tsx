import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { type KeyboardEvent, type ReactNode, useState } from "react";
import { queries } from "../../api/queries";
import type { JobList, JobQuery, JobRow } from "../../api/types";
import { Score, place } from "../../components/JobList";
import { StatusDot } from "../../components/StatusDot";
import { listedOnly, sourceLabel } from "../../domain/sources";
import { when } from "../../lib/format";
import { Link } from "../../lib/router";
import { Ago } from "../../ui/Ago";
import { ArrowOut } from "../../ui/icons";
import { Spinner } from "../../ui/Spinner";
import { JobView } from "../job/JobView";
import styles from "./Jobs.module.css";
import { Pager, jobPages } from "./Pager";

const NEXT_KEYS = new Set(["ArrowDown", "j"]);
const PREVIOUS_KEYS = new Set(["ArrowUp", "k"]);

function Docked({ id }: { id: number }) {
  const { data: job, isError } = useQuery({
    ...queries.job(id),
    placeholderData: keepPreviousData,
  });
  if (isError) {
    return <p className={styles.dockEmpty}>Couldn't load this job. Is the app still running?</p>;
  }
  if (!job) {
    return (
      <p className={styles.dockEmpty}>
        <Spinner />
      </p>
    );
  }
  return (
    <JobView
      key={job.id}
      job={job}
      docked
      more={
        <Link to={`/jobs/${String(job.id)}`}>
          Open on its own page
          <ArrowOut size={11} />
        </Link>
      }
    />
  );
}

function Item({ job, on, onPick }: { job: JobRow; on: boolean; onPick: () => void }) {
  return (
    <li>
      <button
        type="button"
        className={styles.listItem}
        aria-current={on ? "true" : undefined}
        data-job={job.id}
        onClick={onPick}
      >
        <span className={styles.listText}>
          <strong className={styles.listTitle}>{job.title}</strong>
          <span className={styles.listPlace}>
            {listedOnly(job) ? `${place(job)} · ${sourceLabel(job.source)}` : place(job)}
          </span>
        </span>
        <Score value={job.score} />
        <span className={styles.listMeta}>
          <StatusDot status={job.status} auto={job.autoSubmitted} />
          <time dateTime={job.updatedAt} title={when(job.updatedAt)}>
            <Ago iso={job.updatedAt} />
          </time>
        </span>
      </button>
    </li>
  );
}

type JobSplitProps = { query: JobQuery; list: JobList; tools: ReactNode };

export function JobSplit({ query, list, tools }: JobSplitProps) {
  const [picked, setPicked] = useState<number | null>(null);
  const jobs = list.jobs;
  const current = jobs.find((job) => job.id === picked) ?? jobs[0];
  const move = (event: KeyboardEvent<HTMLUListElement>) => {
    const step = NEXT_KEYS.has(event.key) ? 1 : PREVIOUS_KEYS.has(event.key) ? -1 : 0;
    if (step === 0 || !current) return;
    event.preventDefault();
    const next = jobs[jobs.indexOf(current) + step];
    if (!next) return;
    setPicked(next.id);
    event.currentTarget.querySelector<HTMLElement>(`[data-job="${String(next.id)}"]`)?.focus();
  };
  return (
    <div className={styles.split}>
      <div className={styles.listPane}>
        <div className={styles.paneTools}>{tools}</div>
        {jobs.length === 0 ? (
          <p className={styles.listEmpty}>
            <strong>No jobs here</strong>
            {query.q ? `Nothing matches “${query.q}”.` : "Try another filter."}
          </p>
        ) : (
          <ul className={styles.list} aria-label="Jobs" onKeyDown={move}>
            {jobs.map((job) => (
              <Item
                key={job.id}
                job={job}
                on={job === current}
                onPick={() => {
                  setPicked(job.id);
                }}
              />
            ))}
          </ul>
        )}
        <footer className={styles.listFoot}>
          <span className={styles.keys}>
            <kbd>J</kbd>
            <kbd>K</kbd> move
          </span>
          <Pager {...jobPages(query, list)} compact />
        </footer>
      </div>
      <div className={styles.dock} aria-label="Selected job" role="region">
        {current ? <Docked id={current.id} /> : <p className={styles.dockEmpty}>Pick a job.</p>}
      </div>
    </div>
  );
}
