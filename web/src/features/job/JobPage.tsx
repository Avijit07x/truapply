import { useSuspenseQuery } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import { place } from "../../components/JobList";
import type { PageProps } from "../../lib/router";
import { BackToWhereYouWere } from "../../ui/Blocks";
import { AboutMatch } from "./AboutMatch";
import { Description } from "./Description";
import { FilledAnswers } from "./FilledAnswers";
import styles from "./Job.module.css";
import { JobActions } from "./JobActions";
import { JobMeta } from "./JobMeta";
import { NextStep } from "./NextStep";
import { ResumeSection } from "./ResumeSection";

export default function JobPage({ params }: PageProps) {
  const id = Number(params[0]);
  const { data: job } = useSuspenseQuery(queries.job(id));
  return (
    <article className={styles.page}>
      <BackToWhereYouWere fallback="/jobs" />
      <header className={styles.header}>
        <div className={styles.heading}>
          <h1 className={styles.title}>{job.title}</h1>
          <p className={styles.place}>{place(job) || "Location not given"}</p>
          <JobMeta job={job} />
        </div>
        <JobActions job={job} />
      </header>
      <div className={styles.layout}>
        <div className={styles.main}>
          <NextStep job={job} />
          <FilledAnswers job={job} />
          <ResumeSection job={job} />
          {job.description && <Description text={job.description} />}
        </div>
        <AboutMatch job={job} />
      </div>
    </article>
  );
}
