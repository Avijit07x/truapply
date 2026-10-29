import type { ReactNode } from "react";
import type { JobDetail } from "../../api/types";
import { place } from "../../components/JobList";
import { listedOnly } from "../../domain/sources";
import { cx } from "../../lib/cx";
import { AboutMatch } from "./AboutMatch";
import { Description } from "./Description";
import { FilledAnswers } from "./FilledAnswers";
import styles from "./Job.module.css";
import { JobActions } from "./JobActions";
import { JobMeta } from "./JobMeta";
import { NextStep } from "./NextStep";
import { ResumeSection, resumeApplies } from "./ResumeSection";

type JobViewProps = { job: JobDetail; top?: ReactNode; more?: ReactNode; docked?: boolean };

export function JobView({ job, top, more, docked = false }: JobViewProps) {
  return (
    <article className={cx(styles.view, docked && styles.docked)}>
      <header className={styles.header}>
        {top}
        <div className={styles.titleRow}>
          <div className={styles.heading}>
            <h1 className={styles.title}>{job.title}</h1>
            <p className={styles.place}>{place(job) || "Location not given"}</p>
          </div>
          <JobActions job={job} />
        </div>
        <JobMeta job={job}>{more}</JobMeta>
      </header>
      <div className={styles.layout}>
        <div className={styles.main}>
          <NextStep job={job} />
          {!listedOnly(job) && resumeApplies(job) && <ResumeSection job={job} />}
          <FilledAnswers job={job} />
          {job.description && <Description text={job.description} open={listedOnly(job)} />}
        </div>
        <AboutMatch job={job} />
      </div>
    </article>
  );
}
