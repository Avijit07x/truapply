import { useSuspenseQuery } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import { place } from "../../components/JobList";
import type { PageProps } from "../../lib/router";
import { BackLink, PageHeader, Section } from "../../ui/Blocks";
import { Description } from "./Description";
import { FilledAnswers } from "./FilledAnswers";
import styles from "./Job.module.css";
import { JobActions } from "./JobActions";
import { JobFacts } from "./JobFacts";
import { OpenQuestions } from "./OpenQuestions";
import { ResumeSection } from "./ResumeSection";

export default function JobPage({ params }: PageProps) {
  const id = Number(params[0]);
  const { data: job } = useSuspenseQuery(queries.job(id));
  return (
    <article className={styles.page}>
      <PageHeader
        back={<BackLink to="/jobs">All jobs</BackLink>}
        title={job.title}
        description={place(job) || "Location not given"}
      />
      <JobFacts job={job} />
      <JobActions job={job} />
      <OpenQuestions job={job} />
      <FilledAnswers job={job} />
      <ResumeSection job={job} />
      {job.hasScreenshot && (
        <Section title="The form as it was filled in">
          <img
            className={styles.shot}
            src={`/jobs/${String(job.id)}/screenshot.png`}
            alt="Screenshot of the filled-in form"
            loading="lazy"
          />
        </Section>
      )}
      {job.description && <Description text={job.description} />}
    </article>
  );
}
